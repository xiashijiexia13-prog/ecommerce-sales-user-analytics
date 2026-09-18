# -*- coding: utf-8 -*-
"""
电商销售与用户行为分析 · 交互式看板（Streamlit）
====================================================
功能：连接 MySQL，把前面算好的核心指标做成"一眼看懂"的网页看板
用法：在虚拟环境中运行  streamlit run src/dashboard.py
      （要在项目根目录下运行，这样脚本里的 .env 才能被找到）
"""

import os
import streamlit as st
import altair as alt
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 1. 页面全局配置 —— 必须写在所有 st.* 组件之前
st.set_page_config(
    page_title="电商销售与用户行为分析看板",
    page_icon="📊",
    layout="wide",   # 页面铺满宽度，方便后面并排放卡片和图表
)

# 2. 连接数据库（和前几阶段 rfm/留存脚本一样的写法，读 .env 里的账号密码）
load_dotenv(dotenv_path='.env')
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
)

# 2.5 侧边栏筛选器：选品类 + 选月份范围，让"现场查 SQL"的图表跟着联动
#     为什么筛选要放在"查数据"这一步（SQL 的 WHERE）而不是"画图"那一步？
#     因为只有源头的数据变了，后面所有图才会一起变——这正是 BI 看板的核心。

# 先查出数据里有哪些月份，作为月份滑块的"刻度"（比如 ['2024-01','2024-02',...]）
months = pd.read_sql(
    "SELECT DISTINCT DATE_FORMAT(order_time, '%%Y-%%m') AS month "
    "FROM orders_clean ORDER BY month",
    engine,
)['month'].tolist()

with st.sidebar:
    st.header("🔍 筛选")
    categories = ['全部', '3C数码', '家居生活', '服饰鞋包']
    selected_cat = st.selectbox('品类', categories)

    # select_slider：带两个把手的滑块，拖出"起止月份"，返回 (起点, 终点)
    selected_range = st.select_slider(
        '月份范围',
        options=months,
        value=(months[0], months[-1]),   # 默认选全部月份
    )

# 品类条件：
#   选"全部"   -> cat_cond 为空，等于不过滤
#   选具体品类 -> cat_cond = " AND category = 'xxx'"
if selected_cat == '全部':
    cat_cond = ""
else:
    cat_cond = f" AND category = '{selected_cat}'"

# 月份范围条件：DATE_FORMAT 把时间转成 'YYYY-MM' 字符串，再用 BETWEEN 卡起止
start, end = selected_range
month_cond = f" AND DATE_FORMAT(order_time, '%%Y-%%m') BETWEEN '{start}' AND '{end}'"

# 两个条件都是 "AND ..." 开头，直接拼在一起，后面每个查询的 WHERE 都拼上它
filter_cond = cat_cond + month_cond

# 3. 用 SQL 算出 4 个核心 KPI（口径与 sql/03 多维分析完全一致）
kpi_sql = f"""
SELECT
    ROUND(SUM(amount), 2)     AS gmv,          -- 总 GMV（只算已支付）
    COUNT(*)                  AS paid_orders,  -- 已支付订单量
    COUNT(DISTINCT user_id)   AS paid_users    -- 购买用户数（一个用户买多单只算一次）
FROM orders_clean
WHERE status = '已支付'{filter_cond}
"""
kpi = pd.read_sql(kpi_sql, engine).iloc[0]

# 退款率 = 已退款 /（已支付 + 已退款），分母必须包含已退款（口径见 sql/03 第 7 节）
# WHERE 1=1 是动态筛选的常用写法：1=1 永远为真，等于"没有基础过滤"，
# 这样后面可以统一拼 AND 条件（选"全部"时 cat_cond 为空，1=1 就不过滤）
refund_sql = f"""
SELECT
    ROUND(
        SUM(CASE WHEN status = '已退款' THEN 1 ELSE 0 END) /
        SUM(CASE WHEN status IN ('已支付', '已退款') THEN 1 ELSE 0 END) * 100,
        2
    ) AS refund_rate_pct
FROM orders_clean
WHERE 1=1{filter_cond}
"""
refund_rate = pd.read_sql(refund_sql, engine).iloc[0]

# 4. 把查出来的结果转成普通数字，方便格式化
gmv = float(kpi['gmv'])
paid_orders = int(kpi['paid_orders'])
paid_users = int(kpi['paid_users'])
refund_rate_pct = float(refund_rate['refund_rate_pct'])

# 5. 标题 + 一行 4 张 KPI 卡片
st.title("🛒 电商销售与用户行为分析看板")
st.caption("数据来源：orders_clean（已清洗）· 统计口径与 sql/03 多维分析一致")

col1, col2, col3, col4 = st.columns(4)
col1.metric("总 GMV（元）", f"{gmv:,.0f}")
col2.metric("已支付订单量", f"{paid_orders:,}")
col3.metric("购买用户数", f"{paid_users:,}")
col4.metric("退款率", f"{refund_rate_pct:.2f}%")

# 6. 第一张图：每月 GMV 趋势（折线图）
st.subheader("📈 每月 GMV 趋势（已支付）")

monthly_sql = f"""
SELECT
    DATE_FORMAT(order_time, '%%Y-%%m') AS month,
    ROUND(SUM(amount), 2)            AS gmv
FROM orders_clean
WHERE status = '已支付'{filter_cond}
GROUP BY DATE_FORMAT(order_time, '%%Y-%%m')
ORDER BY month
"""
monthly = pd.read_sql(monthly_sql, engine)

line = alt.Chart(monthly).mark_line(
    point=True,          # 每个数据点画个圆点，方便鼠标悬停
    color='#2a78d6',     # 蓝色（看板主序列色）
    strokeWidth=2,       # 细线
).encode(
    x=alt.X('month:N', title='月份', axis=alt.Axis(labelAngle=0)),
    y=alt.Y('gmv:Q', title='GMV（元）', axis=alt.Axis(format=',.0f')),
    tooltip=[
        alt.Tooltip('month:N', title='月份'),
        alt.Tooltip('gmv:Q', title='GMV（元）', format=',.0f'),
    ],
).properties(height=320)

st.altair_chart(line, use_container_width=True)

# 7. 品类 + 渠道 GMV（横向柱状图，分类配色）
st.subheader("📊 品类与渠道结构（已支付 GMV）")

# 7.1 品类 GMV
cat_sql = f"""
SELECT category, ROUND(SUM(amount), 2) AS gmv
FROM orders_clean
WHERE status = '已支付'{filter_cond}
GROUP BY category
ORDER BY gmv DESC
"""
cat = pd.read_sql(cat_sql, engine)
cat['share'] = (cat['gmv'] / cat['gmv'].sum() * 100).round(1)   # 占比%

cat_color = {
    '3C数码':  '#2a78d6',   # 蓝
    '家居生活': '#eb6834',  # 橙
    '服饰鞋包': '#1baf7a',  # 青
}

cat_chart = alt.Chart(cat).mark_bar().encode(
    y=alt.Y('category:N', sort='-x', title=None),   # -x 表示按 x 值从高到低排
    x=alt.X('gmv:Q', title='GMV（元）', axis=alt.Axis(format=',.0f')),
    color=alt.Color('category:N',
                    scale=alt.Scale(domain=list(cat_color.keys()),
                                    range=list(cat_color.values())),
                    legend=None),
    tooltip=[
        alt.Tooltip('category:N', title='品类'),
        alt.Tooltip('gmv:Q', title='GMV（元）', format=',.0f'),
        alt.Tooltip('share:Q', title='占比（%）', format='.1f'),
    ],
).properties(height=220, title='各品类 GMV')

# 7.2 渠道 GMV
chan_sql = f"""
SELECT channel, ROUND(SUM(amount), 2) AS gmv
FROM orders_clean
WHERE status = '已支付'{filter_cond}
GROUP BY channel
ORDER BY gmv DESC
"""
chan = pd.read_sql(chan_sql, engine)
chan['share'] = (chan['gmv'] / chan['gmv'].sum() * 100).round(1)

chan_color = {
    'App':   '#2a78d6',   # 蓝
    '小程序': '#eb6834',  # 橙
    'H5':    '#1baf7a',   # 青
    'PC':    '#eda100',   # 黄
    '未知':   '#e87ba4',  # 品红
}

chan_chart = alt.Chart(chan).mark_bar().encode(
    y=alt.Y('channel:N', sort='-x', title=None),
    x=alt.X('gmv:Q', title='GMV（元）', axis=alt.Axis(format=',.0f')),
    color=alt.Color('channel:N',
                    scale=alt.Scale(domain=list(chan_color.keys()),
                                    range=list(chan_color.values())),
                    legend=None),
    tooltip=[
        alt.Tooltip('channel:N', title='渠道'),
        alt.Tooltip('gmv:Q', title='GMV（元）', format=',.0f'),
        alt.Tooltip('share:Q', title='占比（%）', format='.1f'),
    ],
).properties(height=220, title='各渠道 GMV')

# 7.3 两张图并排放（st.columns(2) 左右各一栏）
left, right = st.columns(2)
with left:
    st.altair_chart(cat_chart, use_container_width=True)
with right:
    st.altair_chart(chan_chart, use_container_width=True)

# 8. RFM 用户分层（读第 6 阶段算好的 CSV）
st.subheader("👥 RFM 用户分层")
st.caption("按全量用户计算（读第 6 阶段算好的 CSV），不受品类筛选影响")

rfm = pd.read_csv('data/rfm_clustered.csv')
cluster_names = {0: '活跃用户', 1: '普通用户', 2: '流失用户', 3: '高价值用户'}
rfm['客户类型'] = rfm['cluster'].map(cluster_names)

# 汇总每类：用户数 + GMV 贡献占比
rfm_sum = rfm.groupby('客户类型').agg(
    用户数=('user_id', 'count'),
    GMV=('M', 'sum'),
).reset_index()
rfm_sum['用户占比(%)'] = (rfm_sum['用户数'] / rfm_sum['用户数'].sum() * 100).round(1)
rfm_sum['GMV占比(%)'] = (rfm_sum['GMV'] / rfm_sum['GMV'].sum() * 100).round(1)
rfm_sum = rfm_sum.sort_values('GMV占比(%)', ascending=False).reset_index(drop=True)

st.dataframe(
    rfm_sum[['客户类型', '用户数', '用户占比(%)', 'GMV占比(%)']],
    use_container_width=True,
    hide_index=True,
)

# 9. 下单转化漏斗（现场查 SQL，一条就够）
st.subheader("🔻 下单转化漏斗")

funnel_sql = f"""
SELECT
    COUNT(*)                                                       AS 下单,
    SUM(CASE WHEN status IN ('已支付', '已退款') THEN 1 ELSE 0 END) AS 支付,
    SUM(CASE WHEN status = '已支付' THEN 1 ELSE 0 END)              AS 完成
FROM orders_clean
WHERE 1=1{filter_cond}
"""
f = pd.read_sql(funnel_sql, engine).iloc[0]

funnel_df = pd.DataFrame({
    '阶段': ['下单', '支付', '完成'],
    '订单量': [int(f['下单']), int(f['支付']), int(f['完成'])],
})

funnel_chart = alt.Chart(funnel_df).mark_bar().encode(
    y=alt.Y('阶段:N', sort='-x', title=None),   # 按订单量从大到小，下单自然排最上
    x=alt.X('订单量:Q', title='订单量（单）', axis=alt.Axis(format=',.0f')),
    color=alt.Color('阶段:N',
                    scale=alt.Scale(domain=['下单', '支付', '完成'],
                                    range=['#86b6ef', '#3987e5', '#184f95']),
                    legend=None),
    tooltip=[alt.Tooltip('阶段:N'), alt.Tooltip('订单量:Q', format=',.0f')],
).properties(height=180, title='下单 → 支付 → 完成')

st.altair_chart(funnel_chart, use_container_width=True)

# 两步转化率（现场算，不写死）
rate1 = f['支付'] / f['下单'] * 100
rate2 = f['完成'] / f['支付'] * 100
st.caption(f"转化率：下单→支付 {rate1:.2f}% · 支付→完成 {rate2:.2f}%")

# 10. 新用户留存热力图（读第 6 阶段算好的 CSV）
st.subheader("📅 新用户留存热力图")
st.caption("按全量用户计算（读第 6 阶段算好的 CSV），不受品类筛选影响")

retention = pd.read_csv('data/retention.csv', index_col=0)

# 转成长表（Altair 热力图需要 行/列/值 三列）
ret_long = retention.reset_index().melt(
    id_vars='首购月', var_name='第N月', value_name='留存率'
)
# 把"第3月"里的数字提取出来，才能按 0,1,2,... 排序（字符串排序会把"第10月"排到"第1月"前面）
ret_long['月数'] = ret_long['第N月'].str.extract(r'(\d+)').astype(int)

heat = alt.Chart(ret_long).mark_rect().encode(
    x=alt.X('月数:O', title='距首购月数',
            axis=alt.Axis(labelAngle=0, labelExpr="'第' + datum.label + '月'")),
    y=alt.Y('首购月:N', sort='descending', title='首购月'),
    color=alt.Color('留存率:Q',
                    scale=alt.Scale(domain=[0, 100],
                                    range=['#cde2fb', '#0d366b']),
                    legend=alt.Legend(title='留存率（%）')),
    tooltip=[alt.Tooltip('首购月:N'), alt.Tooltip('第N月:N'),
             alt.Tooltip('留存率:Q', format='.1f')],
).properties(height=340, title='新用户留存率（%，空白 = 尚未到观察期）')

st.altair_chart(heat, use_container_width=True)

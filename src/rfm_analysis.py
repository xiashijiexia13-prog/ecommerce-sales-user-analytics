# -*- coding: utf-8 -*-
"""
RFM 用户分层分析（第一步：计算 R/F/M 指标）
============================================
功能：从 orders_clean 读取已支付订单，为每个用户计算 R/F/M 三个指标
用法：在虚拟环境中运行  python src/rfm_analysis.py

指标定义：
  R (Recency)   = 最近一次下单距"参考日期"的天数（越小越好）
  F (Frequency) = 已支付订单数（越大越好）
  M (Monetary)  = 已支付订单总金额（越大越好）
"""

import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 1. 连接数据库
load_dotenv(dotenv_path='.env')
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
)

# 2. 只读"已支付"订单 —— RFM 里的"消费"必须是真付过钱的
orders = pd.read_sql(
    "SELECT user_id, order_id, order_time, amount "
    "FROM orders_clean WHERE status = '已支付'",
    engine
)
print(f"已支付订单：{len(orders)} 行")

# 3. 确定"参考日期"：数据最后一天 + 1
#    R 是"距今多少天"，但历史数据没有真正的"今天"，
#    所以把"数据里最后一天的下一天"当成"现在"来算
reference_date = orders['order_time'].max() + pd.Timedelta(days=1)
print(f"参考日期（= 数据最后一天 + 1）：{reference_date.date()}")

# 4. 按 user_id 分组，一次性算出 R/F/M
#    agg：对每个用户的多个字段分别做不同聚合
rfm = orders.groupby('user_id').agg(
    last_order_time=('order_time', 'max'),   # 最近一次下单时间
    F=('order_id', 'count'),                 # 购买次数
    M=('amount', 'sum'),                     # 消费总金额
).reset_index()

# R = 参考日期 − 最近一次下单时间，转成"天数"
rfm['R'] = (reference_date - rfm['last_order_time']).dt.days
rfm = rfm[['user_id', 'R', 'F', 'M']]

# 5. 打印结果
print(f"\n共 {len(rfm)} 个购买用户，RFM 指标计算完成：")
print(rfm.head(10).to_string(index=False))

print("\nR / F / M 分布概况（描述性统计）：")
print(rfm[['R', 'F', 'M']].describe().round(2).to_string())

# 6. 保存中间结果，供下一步 KMeans 聚类使用
os.makedirs('data', exist_ok=True)   # 确保 data 目录存在（exist_ok=True 表示已存在也不报错）
rfm.to_csv('data/rfm.csv', index=False)
print("\n已保存到 data/rfm.csv（下一步聚类用）")

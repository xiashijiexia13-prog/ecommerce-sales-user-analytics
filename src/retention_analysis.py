# -*- coding: utf-8 -*-
"""
留存分析（Cohort 分析）：新用户留存率
=======================================
功能：按用户"首次购买月份"分组，计算每个 cohort 在第 N 个月的留存率
用法：在虚拟环境中运行  python src/retention_analysis.py

口径：留存率 = 某月首次购买的用户中，第 N 个月仍在购买的用户占比
      （第 N 个月买过任意一单就算"留存"，同月买多单只算一次）
"""

import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 1. 连库，只读"已支付"订单（留存看的是"真买过"的用户）
load_dotenv(dotenv_path='.env')
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
)
orders = pd.read_sql(
    "SELECT user_id, order_time FROM orders_clean WHERE status = '已支付'",
    engine
)

# 2. 把下单时间取到"月"粒度（2024-06-15 -> 2024-06）
orders['order_month'] = orders['order_time'].dt.to_period('M')

# 3. 每个用户的"首次购买月份"（用首购当作"成为用户"的起点）
first = orders.groupby('user_id')['order_month'].min()
orders['first_month'] = orders['user_id'].map(first)

# 4. "第 N 个月" = 订单月份 - 首购月份（Period 相减得到 MonthEnd，.n 取出整数月数）
orders['cohort_index'] = (orders['order_month'] - orders['first_month']).apply(lambda x: x.n)

# 5. 去重：一个用户在同一个月买多单，也只算"留存了"一次
active = orders[['user_id', 'first_month', 'cohort_index']].drop_duplicates()

# 6. 每个 cohort 的规模 = 首购月（第 0 月）的用户数
cohort_size = active[active['cohort_index'] == 0].groupby('first_month')['user_id'].nunique()

# 7. 每个 (首购月, 第N月) 的活跃用户数，展开成矩阵（行=首购月，列=第N月）
#    不用 fill_value=0：让"还没到观察期"的格子留空(NaN)，而不是误显示成 0
cohort_counts = active.groupby(['first_month', 'cohort_index'])['user_id'].nunique().unstack()

# 8. 留存率 = 每行 ÷ 该行第 0 月的规模 × 100（×100 转成百分数）
retention = (cohort_counts.div(cohort_size, axis=0) * 100).round(1)

# 9. 美化表头（列名 0/1/2 -> 第0月/第1月/第2月）
retention.columns = [f'第{i}月' for i in retention.columns]
retention.index.name = '首购月'

print("各月新用户的留存率（%）：")
print(retention.to_string())

# 10. 保存
os.makedirs('data', exist_ok=True)
retention.to_csv('data/retention.csv')
print("\n已保存到 data/retention.csv")

# -*- coding: utf-8 -*-
"""
数据清洗脚本
============
功能：读取 MySQL 中的脏数据，按清洗策略逐项修复，写入 orders_clean / users_clean 表
用法：在虚拟环境中运行  python src/data_clean.py
说明：本脚本不修改原始表（orders/users），只生成清洗后的新表，保留原始数据
"""

import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

# 1. 连接数据库，读取数据
load_dotenv(dotenv_path='.env')
engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?charset=utf8mb4"
)

orders = pd.read_sql("SELECT * FROM orders", engine).drop(columns=['id'])  # 去掉代理主键
users = pd.read_sql("SELECT * FROM users", engine)
products = pd.read_sql("SELECT * FROM products", engine)

print("========== 开始清洗 ==========\n")

# 2. 去重：删除重复订单号（保留第一条）
before = len(orders)
orders = orders.drop_duplicates(subset=['order_id'], keep='first')
print(f"[去重]       {before} -> {len(orders)} 行，删除 {before - len(orders)} 条重复订单")

# 3. 缺失值填充：region / channel 填 '未知'
orders['region'] = orders['region'].fillna('未知')
orders['channel'] = orders['channel'].fillna('未知')
print("[填充]       region / channel 缺失值已填 '未知'")

# 4. 修复异常金额：关联商品表，用 单价×数量 重算
orders = orders.merge(products[['product_id', 'price']], on='product_id', how='left')
abnormal = (orders['amount'] < 0) | (orders['amount'] == 0) | (orders['amount'] > 50000)
orders.loc[abnormal, 'amount'] = (orders.loc[abnormal, 'price'] * orders.loc[abnormal, 'quantity']).round(2)
orders = orders.drop(columns=['price'])
print(f"[金额修复]   修复了 {abnormal.sum()} 条异常金额（重算为 单价×数量）")

# 5. 修复时间逻辑错误：交换 pay_time 和 order_time
swap = orders['pay_time'] < orders['order_time']
tmp = orders.loc[swap, 'pay_time'].values
orders.loc[swap, 'pay_time'] = orders.loc[swap, 'order_time'].values
orders.loc[swap, 'order_time'] = tmp
print(f"[时间修复]   交换了 {swap.sum()} 条时间颠倒的订单")

# 6. 修复状态矛盾：已支付但无支付时间 -> 改为待支付
status_fix = (orders['status'] == '已支付') & (orders['pay_time'].isnull())
orders.loc[status_fix, 'status'] = '待支付'
print(f"[状态修复]   修正了 {status_fix.sum()} 条状态矛盾订单")

# 7. 修复年龄异常：0 或 200 -> 用中位数填充
median_age = users['age'].median()
age_fix = (users['age'] == 0) | (users['age'] == 200)
users.loc[age_fix, 'age'] = median_age
print(f"[年龄修复]   修正了 {age_fix.sum()} 条异常年龄（用中位数 {int(median_age)} 填充）")

# 8. 写入清洗后的新表（不动原始表）
orders.to_sql('orders_clean', engine, if_exists='replace', index=False)
users.to_sql('users_clean', engine, if_exists='replace', index=False)
print("\n清洗后数据已写入 orders_clean / users_clean 表")

# 9. 验证清洗结果：重新检查脏数据是否清零
print("\n========== 验证清洗结果 ==========")
print("  剩余 region 缺失        :", orders['region'].isnull().sum())
print("  剩余 channel 缺失       :", orders['channel'].isnull().sum())
print("  剩余重复订单号          :", orders['order_id'].duplicated().sum())
print("  剩余异常金额            :", int(((orders['amount'] < 0) | (orders['amount'] == 0) | (orders['amount'] > 50000)).sum()))
print("  剩余支付早于下单        :", int((orders['pay_time'] < orders['order_time']).sum()))
print("  剩余已支付但空支付时间  :", int(((orders['status'] == '已支付') & (orders['pay_time'].isnull())).sum()))
print("  剩余年龄异常            :", int(((users['age'] == 0) | (users['age'] == 200)).sum()))
print("\n（以上应全部为 0，表示清洗完成）")

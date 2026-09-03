# -*- coding: utf-8 -*-
"""
电商平台销售与用户行为数据生成脚本
====================================
功能：生成 4 张表的数据（用户/商品/订单/行为），并写入 MySQL
用法：在虚拟环境（venv）中运行：  python src/generate_data.py
运行前：确保 ecommerce_analysis 库中 4 张表已建好且为空

设计要点：
  1. 固定随机种子(SEED=42)，任何人运行结果完全一致 -> 可复现
  2. 分层生成：先 users/products，再 orders(引用前两者)，最后 behaviors
  3. 数据贴近真实分布：品类价格区间不同、渠道/订单状态有倾斜
  4. 故意埋入脏数据（供第4阶段清洗）：
     - 缺失值：约1%的 region/channel 为 NULL
     - 重复订单：约1%的 order_id 重复（依赖 orders 表的代理主键 id）
     - 异常金额：约2%的 amount 与 price*quantity 不符（含负数、0、极端值）
     - 时间错误：约1%的 pay_time 早于 order_time
     - 状态矛盾：约1%的"已支付"订单 pay_time 却为 NULL
"""

import os
import random
from datetime import datetime

import numpy as np
import pandas as pd
from faker import Faker
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ================= 1. 读取数据库配置（密码来自 .env，不写死） =================
load_dotenv(dotenv_path='.env')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# ================= 2. 固定随机种子（可复现的关键） =================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
Faker.seed(SEED)

# ================= 3. 数据规模与常量（想改数据量只改这里） =================
N_USERS = 12000       # 用户数（要求 >= 1万）
N_PRODUCTS = 300      # 商品数
N_ORDERS = 55000      # 订单数（要求 >= 5万）
N_BEHAVIORS = 300000  # 行为数（漏斗分析用）

START_DATE = datetime(2024, 6, 1)   # 数据起始（6月，大促月）
END_DATE = datetime(2025, 5, 31)    # 数据结束（共12个月）

CATEGORIES = ['3C数码', '家居生活', '服饰鞋包']
CATEGORY_PRICE_RANGE = {            # 每个品类的单价区间（元），数码贵、服饰便宜
    '3C数码': (500, 15000),
    '家居生活': (50, 2000),
    '服饰鞋包': (30, 800),
}

CHANNELS = ['App', '小程序', 'H5', 'PC']
CHANNEL_WEIGHTS = [0.50, 0.25, 0.15, 0.10]   # 渠道占比：App 最多

fake = Faker('zh_CN')   # 中文假数据生成器


# ================= 4. 工具函数 =================
def random_datetime(start, end, n):
    """在 [start, end] 之间均匀生成 n 个随机时间点（返回 numpy 的 datetime64 数组）"""
    total_seconds = int((end - start).total_seconds())   # 时间段总秒数（小数字，避免 int32 溢出）
    offsets = np.random.randint(0, total_seconds, size=n)  # 随机偏移秒数
    start64 = np.datetime64(start)                         # 起始时间转 numpy 时间
    return (start64 + offsets.astype('timedelta64[s]')).astype('datetime64[ns]')


def weighted_choice(choices, weights, n):
    """按权重从 choices 中抽 n 个（np.random.choice 的封装，返回 object 数组以便塞 None）"""
    return np.random.choice(choices, size=n, p=weights).astype(object)


# ================= 5. 生成用户表 =================
def generate_users(n):
    """生成用户数据，含少量脏数据（1% 异常年龄）"""
    user_id = np.arange(1, n + 1)                          # 显式指定 1,2,3... 供订单引用
    user_name = [fake.name() for _ in range(n)]            # 中文姓名
    gender = np.random.choice(['男', '女'], size=n)         # 性别
    age = np.random.randint(16, 66, size=n)                # 正常年龄 16~65

    # 脏数据：随机 1% 的用户年龄异常（0 或 200）
    dirty_idx = np.random.choice(n, size=int(n * 0.01), replace=False)
    age[dirty_idx] = np.random.choice([0, 200], size=len(dirty_idx))

    register_time = random_datetime(datetime(2023, 6, 1), END_DATE, n)  # 注册时间：跨2023~2025
    region = [fake.city() for _ in range(n)]               # 所在城市
    register_channel = weighted_choice(CHANNELS, CHANNEL_WEIGHTS, n)

    return pd.DataFrame({
        'user_id': user_id,
        'user_name': user_name,
        'gender': gender,
        'age': age,
        'register_time': register_time,
        'region': region,
        'register_channel': register_channel,
    })


# ================= 6. 生成商品表 =================
def generate_products(n):
    """生成商品数据：每个品类价格区间不同，贴近真实"""
    per_cat = n // len(CATEGORIES)                         # 每个品类商品数（均分）
    rows = []
    pid = 1
    for cat in CATEGORIES:
        low, high = CATEGORY_PRICE_RANGE[cat]
        for _ in range(per_cat):
            rows.append({
                'product_id': pid,
                'product_name': f"{cat}-{fake.word().title()}-{pid}",  # 简单商品名
                'category': cat,
                'price': round(np.random.uniform(low, high), 2),        # 品类区间内随机单价
            })
            pid += 1
    return pd.DataFrame(rows)


# ================= 7. 生成订单表（核心，含最多脏数据） =================
def generate_orders(n, users, products):
    """生成订单数据，引用 users 和 products，并埋入多种脏数据"""
    # 建查找表：product_id -> (category, price)，user_id -> region
    cat_map = dict(zip(products['product_id'], products['category']))
    price_map = dict(zip(products['product_id'], products['price']))
    user_region_map = dict(zip(users['user_id'], users['region']))
    prod_ids = products['product_id'].values

    user_id = np.random.choice(users['user_id'].values, size=n)   # 随机挑用户
    product_id = np.random.choice(prod_ids, size=n)               # 随机挑商品
    quantity = np.random.choice([1, 1, 1, 2, 3], size=n)          # 数量：1为主，偶有2、3

    order_time = random_datetime(START_DATE, END_DATE, n)         # 下单时间（12个月内均匀）

    # 订单状态：已支付为主（80%），其余为退款/待支付/取消
    status = np.random.choice(['已支付', '已退款', '待支付', '已取消'],
                              size=n, p=[0.80, 0.05, 0.10, 0.05])

    # ---- 金额：正常 = 单价 * 数量 ----
    price_arr = np.array([price_map[pid] for pid in product_id])
    amount = (price_arr * quantity).round(2)

    # 脏数据①：随机 2% 金额异常（一半是极端值，一半是随机错值）
    n_amount_dirty = int(n * 0.02)
    dirty_idx = np.random.choice(n, size=n_amount_dirty, replace=False)
    extreme = np.random.choice([-999.0, 0.0, 0.01, 99999.0], size=n_amount_dirty)
    random_wrong = np.round(np.random.uniform(1, 5000, n_amount_dirty), 2)
    use_random = np.random.rand(n_amount_dirty) < 0.5
    amount[dirty_idx] = np.where(use_random, random_wrong, extreme)

    # ---- 支付时间：已支付/已退款才有 pay_time，且晚于下单 ----
    pay_time = np.full(n, np.datetime64('NaT', 'ns'), dtype='datetime64[ns]')
    paid_mask = np.isin(status, ['已支付', '已退款'])
    pay_time[paid_mask] = order_time[paid_mask] + \
        np.random.randint(60, 7200, size=paid_mask.sum()).astype('timedelta64[s]')  # 下单后1分钟~2小时支付

    # 脏数据②：随机 1% 的"已支付"订单 pay_time 早于 order_time（时间逻辑错误）
    paid_idx = np.where(paid_mask)[0]
    n_time_dirty = int(n * 0.01)
    time_dirty_idx = np.random.choice(paid_idx, size=n_time_dirty, replace=False)
    pay_time[time_dirty_idx] = order_time[time_dirty_idx] - \
        np.random.randint(3600, 86400, size=n_time_dirty).astype('timedelta64[s]')

    # 脏数据③：随机 1% 的"已支付"订单 pay_time 却为 NULL（状态矛盾）
    n_status_dirty = int(n * 0.01)
    status_dirty_idx = np.random.choice(paid_idx, size=n_status_dirty, replace=False)
    pay_time[status_dirty_idx] = np.datetime64('NaT', 'ns')

    # ---- 地区和渠道 ----
    channel = weighted_choice(CHANNELS, CHANNEL_WEIGHTS, n)
    region = np.array([user_region_map[uid] for uid in user_id], dtype=object)  # 订单地区=用户地区

    # 脏数据④：随机 1% region 缺失、1% channel 缺失
    region[np.random.choice(n, size=int(n * 0.01), replace=False)] = None
    channel[np.random.choice(n, size=int(n * 0.01), replace=False)] = None

    # 订单号：顺序生成，保证唯一（真实订单号通常还会嵌入日期）
    order_id = [f"OD{i:010d}" for i in range(1, n + 1)]

    df = pd.DataFrame({
        'order_id': order_id,
        'user_id': user_id,
        'product_id': product_id,
        'category': [cat_map[pid] for pid in product_id],
        'quantity': quantity,
        'amount': amount,
        'order_time': order_time,
        'pay_time': pay_time,
        'status': status,
        'region': region,
        'channel': channel,
    })

    # 脏数据⑤：随机 1% 订单重复（复制整行，order_id 相同 -> 表里出现重复订单号）
    n_dup = int(n * 0.01)
    dup_idx = np.random.choice(n, size=n_dup, replace=False)
    dup_rows = df.iloc[dup_idx].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df


# ================= 8. 生成行为表（为漏斗分析准备） =================
def generate_behaviors(n, users, products):
    """生成行为数据：浏览 > 加购 > 下单 > 支付，呈漏斗分布"""
    user_id = np.random.choice(users['user_id'].values, size=n)
    product_id = np.random.choice(products['product_id'].values, size=n)
    behavior_type = np.random.choice(['浏览', '加购', '下单', '支付'],
                                     size=n, p=[0.70, 0.15, 0.10, 0.05])
    behavior_time = random_datetime(START_DATE, END_DATE, n)
    channel = weighted_choice(CHANNELS, CHANNEL_WEIGHTS, n)

    return pd.DataFrame({
        'user_id': user_id,
        'product_id': product_id,
        'behavior_type': behavior_type,
        'behavior_time': behavior_time,
        'channel': channel,
    })


# ================= 9. 主流程：生成 -> 写入 MySQL =================
def main():
    print("开始生成数据 ...")

    # 分层生成（先父后子）
    users = generate_users(N_USERS)
    print(f"  [1/4] 用户表生成完成：{len(users)} 行")
    products = generate_products(N_PRODUCTS)
    print(f"  [2/4] 商品表生成完成：{len(products)} 行")
    orders = generate_orders(N_ORDERS, users, products)
    print(f"  [3/4] 订单表生成完成：{len(orders)} 行（含约1%重复订单）")
    behaviors = generate_behaviors(N_BEHAVIORS, users, products)
    print(f"  [4/4] 行为表生成完成：{len(behaviors)} 行")

    # 连接数据库（密码来自 .env，不写死）
    engine = create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )

    # 按顺序写入（先父后子；method='multi' 用批量 INSERT 加速）
    print("\n开始写入 MySQL ...")
    users.to_sql('users', engine, if_exists='append', index=False, method='multi', chunksize=5000)
    print("  users 写入完成")
    products.to_sql('products', engine, if_exists='append', index=False, method='multi', chunksize=5000)
    print("  products 写入完成")
    orders.to_sql('orders', engine, if_exists='append', index=False, method='multi', chunksize=5000)
    print("  orders 写入完成")
    behaviors.to_sql('behaviors', engine, if_exists='append', index=False, method='multi', chunksize=20000)
    print("  behaviors 写入完成")

    print("\n========== 全部完成 ==========")
    print(f"  用户表：{len(users)} 行")
    print(f"  商品表：{len(products)} 行")
    print(f"  订单表：{len(orders)} 行（含脏数据）")
    print(f"  行为表：{len(behaviors)} 行")


if __name__ == '__main__':
    main()

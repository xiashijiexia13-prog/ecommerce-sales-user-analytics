-- ============================================================
-- 电商平台销售与用户行为分析 · 数据质量检查（SQL 版）
-- 数据库：ecommerce_analysis
-- 说明：按"数据质量6维度"逐项检查脏数据，结果供第4阶段清洗使用
-- ============================================================

-- 1. 完整性检查：订单表里 region（收货地区）缺失的行数
SELECT COUNT(*) AS region_missing
FROM orders
WHERE region IS NULL;

-- 2. 完整性检查：订单表里 channel（下单渠道）缺失的行数
SELECT COUNT(*) AS channel_missing
FROM orders
WHERE channel IS NULL;

-- 3. 唯一性检查：重复的订单号（同一个 order_id 出现 > 1 次）
SELECT order_id, COUNT(*) AS cnt
FROM orders
GROUP BY order_id
HAVING COUNT(*) > 1
ORDER BY cnt DESC;

-- 4. 准确性检查：金额异常的订单（负数 / 0 / 超过5万的极端值）
SELECT order_id, amount
FROM orders
WHERE amount < 0 OR amount = 0 OR amount > 50000;

-- 5. 一致性检查：支付时间早于下单时间的错误订单（时间逻辑错误）
SELECT order_id, order_time, pay_time
FROM orders
WHERE pay_time < order_time;

-- 6. 一致性检查：状态为"已支付"但支付时间为空的矛盾订单
SELECT order_id, status, pay_time
FROM orders
WHERE status = '已支付' AND pay_time IS NULL;

-- 7. 有效性检查：年龄异常的用户（0 岁或 200 岁，超出合理范围）
SELECT user_id, age
FROM users
WHERE age = 0 OR age = 200;

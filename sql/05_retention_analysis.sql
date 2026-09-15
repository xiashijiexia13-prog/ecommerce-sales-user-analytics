-- ============================================================
-- 留存分析（SQL 版）—— 仅供对比学习，实际项目用 Python 实现
-- 数据库：ecommerce_analysis
-- 说明：这条 SQL 能算出和 src/retention_analysis.py 一样的结果，
--       但"转成留存率矩阵"这一步要写满 12 个月的重复代码
--       （12 个 LEFT JOIN + 12 列 ROUND），远不如 Python 的
--       .unstack() / .div() 一行来得干净。留作"SQL vs Python 分工"的案例。
-- ============================================================

-- 第一步：每个用户的首次购买月份
WITH user_first AS (
    SELECT user_id, DATE_FORMAT(MIN(order_time), '%Y-%m') AS first_month
    FROM orders_clean
    WHERE status = '已支付'
    GROUP BY user_id
),

-- 第二步：每笔订单相对首购月的"第 N 个月"
user_orders AS (
    SELECT
        o.user_id,
        u.first_month,
        TIMESTAMPDIFF(MONTH, STR_TO_DATE(CONCAT(u.first_month, '-01'), '%Y-%m-%d'), o.order_time) AS cohort_index
    FROM orders_clean o
    JOIN user_first u ON o.user_id = u.user_id
    WHERE o.status = '已支付'
),

-- 第三步：每个 (首购月, 第N月) 的去重用户数
cohort_counts AS (
    SELECT first_month, cohort_index, COUNT(DISTINCT user_id) AS active_users
    FROM user_orders
    GROUP BY first_month, cohort_index
),

-- 每个首购月的用户规模（分母）
cohort_size AS (
    SELECT first_month, COUNT(DISTINCT user_id) AS total_users
    FROM user_first
    GROUP BY first_month
)

-- 第四步：转成宽表矩阵（痛苦点：每个"第N月"都要各 JOIN 一次、各写一列）
SELECT
    s.first_month                                       AS 首购月,
    s.total_users                                       AS 用户数,
    ROUND(100.0 * c0.active_users / s.total_users, 1)   AS 第0月,
    ROUND(100.0 * c1.active_users / s.total_users, 1)   AS 第1月,
    ROUND(100.0 * c2.active_users / s.total_users, 1)   AS 第2月,
    ROUND(100.0 * c3.active_users / s.total_users, 1)   AS 第3月
    -- ...第4月、第5月……一直到第11月，每个都要再写一遍
FROM cohort_size s
LEFT JOIN cohort_counts c0 ON s.first_month = c0.first_month AND c0.cohort_index = 0
LEFT JOIN cohort_counts c1 ON s.first_month = c1.first_month AND c1.cohort_index = 1
LEFT JOIN cohort_counts c2 ON s.first_month = c2.first_month AND c2.cohort_index = 2
LEFT JOIN cohort_counts c3 ON s.first_month = c3.first_month AND c3.cohort_index = 3
    -- ...每个第N月都要再 JOIN 一次
ORDER BY s.first_month;

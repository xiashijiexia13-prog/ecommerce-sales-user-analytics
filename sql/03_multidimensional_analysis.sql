-- ============================================================
-- 电商平台销售与用户行为分析 · 多维分析（SQL 版）
-- 数据库：ecommerce_analysis
-- 说明：对清洗后的数据（orders_clean）做「人货场钱」四维度分析
-- 口径：GMV / 订单数只统计 status='已支付' 的订单；
--       退款订单单独拆出分析（见第 7 节），避免重复计算销售额
-- ============================================================

-- ------------------------------------------------------------
-- 1. 销售总览（钱）：总 GMV、总订单数、客单价
-- 客单价 = 总销售额 / 订单数
-- ------------------------------------------------------------
SELECT
    ROUND(SUM(amount), 2)                     AS gmv,       -- 总销售额（元）
    COUNT(*)                                  AS order_cnt, -- 订单数
    ROUND(SUM(amount) / COUNT(*), 2)          AS aov        -- 客单价
FROM orders_clean
WHERE status = '已支付';

-- ------------------------------------------------------------
-- 2. 商品维度（货）：各品类 GMV / 订单数 / 客单价
-- 结论：3C数码占全平台 GMV 的 85%，但订单量仅 1/3 —— 高客单低频率
--      服饰鞋包订单量最多，客单价最低（633 元），"走量不走价"
-- ------------------------------------------------------------
SELECT
    category,
    ROUND(SUM(amount), 2)                     AS gmv,
    COUNT(*)                                  AS order_cnt,
    ROUND(SUM(amount) / COUNT(*), 2)          AS aov
FROM orders_clean
WHERE status = '已支付'
GROUP BY category
ORDER BY gmv DESC;

-- ------------------------------------------------------------
-- 3. 时间维度（场）：每月 GMV 走势
-- 用 DATE_FORMAT 把下单时间抹平成「年-月」再分组
-- 结论：整体平稳，2025-02（春节）为低谷
-- ------------------------------------------------------------
SELECT
    DATE_FORMAT(order_time, '%Y-%m')          AS month,
    ROUND(SUM(amount), 2)                     AS gmv
FROM orders_clean
WHERE status = '已支付'
GROUP BY DATE_FORMAT(order_time, '%Y-%m')
ORDER BY month;

-- ------------------------------------------------------------
-- 4. 渠道维度（场）：各渠道 GMV / 订单数 / 客单价
-- 结论：App 贡献近 50% GMV，是绝对主力；PC 最弱
--      「未知」= 清洗时对 NULL 渠道填充 '未知' 的结果（约 1%）
-- ------------------------------------------------------------
SELECT
    channel,
    ROUND(SUM(amount), 2)                     AS gmv,
    COUNT(*)                                  AS order_cnt,
    ROUND(SUM(amount) / COUNT(*), 2)          AS aov
FROM orders_clean
WHERE status = '已支付'
GROUP BY channel
ORDER BY gmv DESC;

-- ------------------------------------------------------------
-- 5. 地区维度（场）：GMV 超 100 万的地区（用 HAVING 过滤小地区）
-- 数据发现：同一城市出现「市/县」两种后缀（如哈尔滨市 vs 哈尔滨县），
--           属「同义异名」问题，会拆散真实规模，分析时应先做名称标准化
-- ------------------------------------------------------------
SELECT
    region,
    ROUND(SUM(amount), 2)                     AS gmv,
    COUNT(*)                                  AS order_cnt
FROM orders_clean
WHERE status = '已支付'
GROUP BY region
HAVING SUM(amount) > 1000000
ORDER BY gmv DESC;

-- ------------------------------------------------------------
-- 6. 用户维度（人）：复购率
-- 复购用户 = 购买次数 >= 2 的用户；复购率 = 复购用户数 / 购买用户总数
-- 第一步：复购用户数
-- ------------------------------------------------------------
SELECT COUNT(*) AS repeat_users
FROM (
    SELECT user_id
    FROM orders_clean
    WHERE status = '已支付'
    GROUP BY user_id
    HAVING COUNT(*) >= 2
) AS t;

-- 第二步：购买用户总数（COUNT DISTINCT 去重，一个用户买多单只算一次）
SELECT COUNT(DISTINCT user_id) AS total_users
FROM orders_clean
WHERE status = '已支付';

-- 复购率 = repeat_users / total_users
-- 注：本数据用户基数小(1.2万)、订单多(4.35万)且随机分配，
--     导致复购率约 90%，这是合成数据的生成机制所致，不代表真实业务

-- ------------------------------------------------------------
-- 7. 退款分析（健康度）：退款率
-- 口径：退款率 = 退款订单数 / (已支付 + 已退款)
--      分母必须包含"已退款"，因为退款订单也属于"支付过"的订单
-- 第一步：看各状态订单数（全貌，不加 WHERE）
-- ------------------------------------------------------------
SELECT
    status,
    COUNT(*)                                  AS order_cnt
FROM orders_clean
GROUP BY status
ORDER BY order_cnt DESC;

-- 第二步：直接用一条 SQL 算出退款率（CASE WHEN 条件计数）
SELECT
    SUM(CASE WHEN status = '已退款' THEN 1 ELSE 0 END)                    AS refund_cnt,
    SUM(CASE WHEN status IN ('已支付', '已退款') THEN 1 ELSE 0 END)        AS paid_cnt,
    ROUND(
        SUM(CASE WHEN status = '已退款' THEN 1 ELSE 0 END) /
        SUM(CASE WHEN status IN ('已支付', '已退款') THEN 1 ELSE 0 END) * 100,
        2
    )                                                                     AS refund_rate_pct
FROM orders_clean;

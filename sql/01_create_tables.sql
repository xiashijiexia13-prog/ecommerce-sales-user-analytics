-- ============================================================
-- 电商平台销售与用户行为分析 · 建表脚本
-- 数据库：ecommerce_analysis
-- 说明：本脚本创建 4 张表，可重复执行（用了 IF NOT EXISTS）
-- ============================================================

-- 设置字符集，避免中文乱码
SET NAMES utf8mb4;

-- ------------------------------------------------------------
-- 1. 用户表 users
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id          INT          NOT NULL AUTO_INCREMENT COMMENT '用户ID（主键，自增）',
    user_name        VARCHAR(50)  NOT NULL                COMMENT '用户昵称',
    gender           VARCHAR(10)  DEFAULT NULL            COMMENT '性别',
    age              INT          DEFAULT NULL            COMMENT '年龄',
    register_time    DATETIME     DEFAULT NULL            COMMENT '注册时间',
    region           VARCHAR(50)  DEFAULT NULL            COMMENT '所在城市',
    register_channel VARCHAR(20)  DEFAULT NULL            COMMENT '注册渠道（App/小程序/H5/PC）',
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- ------------------------------------------------------------
-- 2. 商品表 products
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_id    INT           NOT NULL AUTO_INCREMENT COMMENT '商品ID（主键，自增）',
    product_name  VARCHAR(100)  NOT NULL                COMMENT '商品名称',
    category      VARCHAR(30)   NOT NULL                COMMENT '品类（3C数码/家居生活/服饰鞋包）',
    price         DECIMAL(10,2) NOT NULL                COMMENT '单价（元），金额用DECIMAL不用FLOAT',
    PRIMARY KEY (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- ------------------------------------------------------------
-- 3. 订单表 orders（核心表，数据量最大）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id    VARCHAR(32)   NOT NULL                COMMENT '订单ID（字符串，模拟真实订单号）',
    user_id     INT           NOT NULL                COMMENT '用户ID（关联 users.user_id）',
    product_id  INT           NOT NULL                COMMENT '商品ID（关联 products.product_id）',
    category    VARCHAR(30)   NOT NULL                COMMENT '品类（冗余存储，避免频繁关联商品表）',
    quantity    INT           NOT NULL DEFAULT 1      COMMENT '购买数量',
    amount      DECIMAL(12,2) NOT NULL                COMMENT '订单金额（元），正常=单价×数量',
    order_time  DATETIME      NOT NULL                COMMENT '下单时间',
    pay_time    DATETIME      DEFAULT NULL            COMMENT '支付时间（未支付订单为 NULL）',
    status      VARCHAR(20)   NOT NULL                COMMENT '订单状态（已支付/已退款/待支付/已取消）',
    region      VARCHAR(50)   DEFAULT NULL            COMMENT '收货地区',
    channel     VARCHAR(20)   DEFAULT NULL            COMMENT '下单渠道',
    PRIMARY KEY (order_id),
    KEY idx_user_id (user_id),          -- 索引：按用户查订单时加速
    KEY idx_order_time (order_time),    -- 索引：按时间查销售趋势时加速
    KEY idx_category (category)         -- 索引：按品类分析时加速
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表（核心表）';

-- ------------------------------------------------------------
-- 4. 行为表 behaviors（为第6阶段漏斗分析准备）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS behaviors (
    behavior_id    BIGINT       NOT NULL AUTO_INCREMENT COMMENT '行为ID（主键，自增，BIGINT因数据量大）',
    user_id        INT          NOT NULL                COMMENT '用户ID',
    product_id     INT          NOT NULL                COMMENT '商品ID',
    behavior_type  VARCHAR(20)  NOT NULL                COMMENT '行为类型（浏览/加购/下单/支付）',
    behavior_time  DATETIME     NOT NULL                COMMENT '行为发生时间',
    channel        VARCHAR(20)  DEFAULT NULL            COMMENT '渠道',
    PRIMARY KEY (behavior_id),
    KEY idx_user_id (user_id),          -- 索引：按用户查行为时加速
    KEY idx_behavior_time (behavior_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户行为表（漏斗分析用）';

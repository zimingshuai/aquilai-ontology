-- 供应商对账域 DDL（SRM + WMS + FIM 三系统合并导出，2026-10 导出）
-- 注意：三系统各自建表，主键均为业务编码；外键未建约束，业务含义见数据字典

CREATE TABLE supplier (
    supplier_code      VARCHAR(32)  NOT NULL,   -- 供应商编码（SRM 主键）
    supplier_name      VARCHAR(128) NOT NULL,   -- 供应商名称
    settlement_type    VARCHAR(16),             -- 结算方式：月结30天/月结60天/货到付款
    frozen_flag        TINYINT(1)   DEFAULT 0,  -- 冻结标记：1=冻结（停止对账与付款）
    create_time        DATETIME,                -- 创建时间
    update_time        DATETIME,                -- 更新时间
    PRIMARY KEY (supplier_code)
);

CREATE TABLE purchase_contract (
    contract_nr        VARCHAR(64)  NOT NULL,   -- 采购合同号（SRM 主键）
    supplier_code      VARCHAR(32)  NOT NULL,   -- 签约供应商
    contract_amount    DECIMAL(18,2),           -- 合同总金额（含税，元）
    sign_date          DATE,                    -- 签约日期
    status             VARCHAR(16),             -- 生效/终止/作废
    PRIMARY KEY (contract_nr)
);

CREATE TABLE delivery_record (
    delivery_nr        VARCHAR(64)  NOT NULL,   -- 交货单号（WMS 主键）
    contract_nr        VARCHAR(64)  NOT NULL,   -- 关联合同
    delivery_qty       DOUBLE,                  -- 交货数量（件）
    delivery_amount    DECIMAL(18,2),           -- 交货金额（元，含税）
    delivery_date      DATE,                    -- 交货日期
    PRIMARY KEY (delivery_nr)
);

CREATE TABLE reconciliation_statement (
    recon_nr           VARCHAR(64)  NOT NULL,   -- 对账单号（FIM 主键）
    supplier_code      VARCHAR(32)  NOT NULL,   -- 对账供应商
    recon_period       VARCHAR(16),             -- 对账期间（yyyy-MM）
    invoice_amount     DECIMAL(18,2),           -- 发票金额（元，供应商开具）
    reconciled_amount  DECIMAL(18,2),           -- 已对账金额（元，双方确认一致部分）
    status             VARCHAR(16),             -- open=对账中 / confirmed=已确认 / disputed=有争议
    create_time        DATETIME,                -- 单据创建时间
    PRIMARY KEY (recon_nr)
);

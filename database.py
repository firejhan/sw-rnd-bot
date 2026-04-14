"""
database.py — 情报数据库
存储所有抓取到的竞品数据、变化记录、分析结果
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "intel.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，第一次运行时自动创建所有表"""
    with get_conn() as conn:
        conn.executescript("""
            -- 促销页面快照
            CREATE TABLE IF NOT EXISTS promo_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor  TEXT NOT NULL,
                url         TEXT NOT NULL,
                content     TEXT,
                content_hash TEXT,
                fetched_at  TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- 变化记录（新旧对比）
            CREATE TABLE IF NOT EXISTS changes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor    TEXT NOT NULL,
                change_type   TEXT NOT NULL,  -- promo/ad/social/seo
                old_content   TEXT,
                new_content   TEXT,
                summary       TEXT,           -- Claude 生成的变化摘要
                severity      TEXT DEFAULT 'normal',  -- normal/high/urgent
                detected_at   TEXT DEFAULT (datetime('now', 'localtime')),
                reported      INTEGER DEFAULT 0
            );

            -- Facebook 广告记录
            CREATE TABLE IF NOT EXISTS fb_ads (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor    TEXT NOT NULL,
                ad_id         TEXT UNIQUE,
                ad_text       TEXT,
                creative_url  TEXT,
                started_at    TEXT,
                fetched_at    TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- 每日情报报告
            CREATE TABLE IF NOT EXISTS daily_reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date TEXT UNIQUE,
                content     TEXT,
                sent        INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now', 'localtime'))
            );

            -- 系统日志
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                level      TEXT,
                message    TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
    print("✅ 数据库初始化完成")


def hash_content(text: str) -> str:
    """生成内容的MD5哈希，用于检测变化"""
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


def get_last_snapshot(competitor: str) -> dict | None:
    """获取某竞品的最后一次页面快照"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM promo_snapshots 
               WHERE competitor = ? 
               ORDER BY fetched_at DESC LIMIT 1""",
            (competitor,)
        ).fetchone()
        return dict(row) if row else None


def save_snapshot(competitor: str, url: str, content: str):
    """保存页面快照"""
    content_hash = hash_content(content)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO promo_snapshots (competitor, url, content, content_hash)
               VALUES (?, ?, ?, ?)""",
            (competitor, url, content, content_hash)
        )
    return content_hash


def record_change(competitor: str, change_type: str, old_content: str,
                  new_content: str, summary: str = "", severity: str = "normal"):
    """记录检测到的变化"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO changes 
               (competitor, change_type, old_content, new_content, summary, severity)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (competitor, change_type, old_content, new_content, summary, severity)
        )


def get_unreported_changes() -> list:
    """获取所有还没有报告过的变化"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM changes WHERE reported = 0
               ORDER BY severity DESC, detected_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def mark_changes_reported(change_ids: list):
    """标记变化已经报告"""
    if not change_ids:
        return
    placeholders = ",".join("?" * len(change_ids))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE changes SET reported = 1 WHERE id IN ({placeholders})",
            change_ids
        )


def save_daily_report(report_date: str, content: str):
    """保存每日报告"""
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO daily_reports (report_date, content)
               VALUES (?, ?)""",
            (report_date, content)
        )


def mark_report_sent(report_date: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE daily_reports SET sent = 1 WHERE report_date = ?",
            (report_date,)
        )


def log(level: str, message: str):
    """写入系统日志"""
    print(f"[{level.upper()}] {message}")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO logs (level, message) VALUES (?, ?)",
            (level, message)
        )

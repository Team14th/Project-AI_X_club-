using System;
using System.Collections.Generic;

namespace ToolVisualization
{
    /// <summary>
    /// WebSocket 消息的根结构
    /// </summary>
    [Serializable]
    public class WsMessageDto
    {
        public string type;
        public string payload;
    }

    #region Payload DTOs

    /// <summary>
    /// 初始化事件 (type = "init")
    /// </summary>
    [Serializable]
    public class InitDto
    {
        public string tool_name;
        public int total_inventory;
        public int current_inventory;
        public List<BorrowHistoryRecordDto> history_records;
        public List<AlarmHistoryDto> alarm_history;
    }

    /// <summary>
    /// 借出事件 (type = "borrow")
    /// </summary>
    [Serializable]
    public class BorrowEventDto
    {
        public string record_id;
        public string user;
        public int count;
        public string time;
        public int current_inventory;
    }

    /// <summary>
    /// 归还事件 (type = "return")
    /// </summary>
    [Serializable]
    public class ReturnEventDto
    {
        public string record_id;
        public int count;
        public string time;
        public int current_inventory;
    }

    /// <summary>
    /// 库存告警事件 (type = "inventory_alarm")
    /// </summary>
    [Serializable]
    public class InventoryAlarmDto
    {
        public string alarm_id;
        public string reason;
        public int current_inventory;
        public string timestamp;
    }

    /// <summary>
    /// 失败告警事件 (type = "failure_alarm")
    /// </summary>
    [Serializable]
    public class FailureAlarmDto
    {
        public string alarm_id;
        public string reason;
        public string details;
        public string timestamp;
    }

    #endregion

    #region History DTOs (for Init)

    /// <summary>
    /// 历史借还记录 (用于初始化)
    /// </summary>
    [Serializable]
    public class BorrowHistoryRecordDto
    {
        public string record_id;
        public string user;
        public int borrow_count;
        public string borrow_time;
        public int? return_count;
        public string return_time;
    }

    /// <summary>
    /// 历史失败告警记录 (用于初始化)
    /// </summary>
    [Serializable]
    public class AlarmHistoryDto
    {
        public string alarm_id;
        public string reason;
        public string details;
        public string timestamp;
    }

    #endregion
}

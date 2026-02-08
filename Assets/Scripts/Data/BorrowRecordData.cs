using System;

namespace ToolVisualization
{
    /// <summary>
    /// 借还记录领域模型
    /// 表示一次完整的借还行为 (包含借出和归还两个阶段)
    /// </summary>
    public class BorrowRecord
    {
        /// <summary>
        /// 业务记录 ID (唯一标识)
        /// </summary>
        public string RecordId { get; private set; }

        /// <summary>
        /// 借用人姓名
        /// </summary>
        public string User { get; private set; }

        /// <summary>
        /// 借出数量
        /// </summary>
        public int BorrowCount { get; private set; }

        /// <summary>
        /// 借出时间
        /// </summary>
        public string BorrowTime { get; private set; }

        /// <summary>
        /// 归还数量 (可能为 0,表示未归还)
        /// </summary>
        public int ReturnCount { get; private set; }

        /// <summary>
        /// 归还时间 (可能为 null,表示未归还)
        /// </summary>
        public string ReturnTime { get; private set; }

        /// <summary>
        /// 是否已归还
        /// </summary>
        public bool IsReturned => !string.IsNullOrEmpty(ReturnTime);

        /// <summary>
        /// 构造函数 (创建借出记录)
        /// </summary>
        public BorrowRecord(string recordId, string user, int borrowCount, string borrowTime)
        {
            RecordId = recordId;
            User = user;
            BorrowCount = borrowCount;
            BorrowTime = borrowTime;
            ReturnCount = 0;
            ReturnTime = null;
        }

        /// <summary>
        /// 应用归还事件
        /// </summary>
        public void ApplyReturn(int returnCount, string returnTime)
        {
            ReturnCount = returnCount;
            ReturnTime = returnTime;
        }

        /// <summary>
        /// 从 DTO 创建借出记录
        /// </summary>
        public static BorrowRecord FromBorrowDto(BorrowEventDto dto)
        {
            return new BorrowRecord(dto.record_id, dto.user, dto.count, dto.time);
        }

        /// <summary>
        /// 从历史记录 DTO 创建完整记录
        /// </summary>
        public static BorrowRecord FromHistoryDto(BorrowHistoryRecordDto dto)
        {
            var record = new BorrowRecord(dto.record_id, dto.user, dto.borrow_count, dto.borrow_time);

            if (dto.return_count.HasValue && !string.IsNullOrEmpty(dto.return_time))
            {
                record.ApplyReturn(dto.return_count.Value, dto.return_time);
            }

            return record;
        }
    }

    /// <summary>
    /// 失败报警领域模型
    /// </summary>
    public class FailureAlarmRecord
    {
        /// <summary>
        /// 报警唯一 ID
        /// </summary>
        public string AlarmId { get; private set; }

        /// <summary>
        /// 报警原因
        /// </summary>
        public string Reason { get; private set; }

        /// <summary>
        /// 详细信息
        /// </summary>
        public string Details { get; private set; }

        /// <summary>
        /// 报警时间
        /// </summary>
        public string Timestamp { get; private set; }

        /// <summary>
        /// 构造函数
        /// </summary>
        public FailureAlarmRecord(string alarmId, string reason, string details, string timestamp)
        {
            AlarmId = alarmId;
            Reason = reason;
            Details = details;
            Timestamp = timestamp;
        }

        /// <summary>
        /// 从 DTO 创建报警记录
        /// </summary>
        public static FailureAlarmRecord FromDto(FailureAlarmDto dto)
        {
            return new FailureAlarmRecord(dto.alarm_id, dto.reason, dto.details, dto.timestamp);
        }

        /// <summary>
        /// 从历史记录 DTO 创建报警记录
        /// </summary>
        public static FailureAlarmRecord FromHistoryDto(AlarmHistoryDto dto)
        {
            return new FailureAlarmRecord(dto.alarm_id, dto.reason, dto.details, dto.timestamp);
        }
    }

    /// <summary>
    /// 库存数据模型
    /// </summary>
    public class InventoryData
    {
        /// <summary>
        /// 工具名称
        /// </summary>
        public string ToolName { get; private set; }

        /// <summary>
        /// 总库存
        /// </summary>
        public int TotalInventory { get; private set; }

        /// <summary>
        /// 当前剩余库存
        /// </summary>
        public int CurrentInventory { get; private set; }

        /// <summary>
        /// 构造函数
        /// </summary>
        public InventoryData(string toolName, int totalInventory, int currentInventory)
        {
            ToolName = toolName;
            TotalInventory = totalInventory;
            CurrentInventory = currentInventory;
        }

        /// <summary>
        /// 更新当前库存
        /// </summary>
        public void UpdateCurrentInventory(int newInventory)
        {
            CurrentInventory = newInventory;
        }

        /// <summary>
        /// 从 Init DTO 创建库存数据
        /// </summary>
        public static InventoryData FromInitDto(InitDto dto)
        {
            return new InventoryData(dto.tool_name, dto.total_inventory, dto.current_inventory);
        }
    }
}

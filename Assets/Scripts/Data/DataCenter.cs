using System;
using System.Collections.Generic;
using UnityEngine;

namespace ToolVisualization
{
    /// <summary>
    /// 前端数据中心 (单一数据源)
    /// 负责维护所有业务领域模型,并将 WebSocket 接收的 DTO 事件转化为领域事件,通知 UI 更新。
    /// </summary>
    public class DataCenter
    {
        #region Singleton

        private static DataCenter _instance;
        public static DataCenter Instance => _instance ?? (_instance = new DataCenter());

        #endregion

        #region Events

        /// <summary>
        /// 当历史记录加载完成时触发
        /// </summary>
        public event Action OnHistoryLoaded;

        /// <summary>
        /// 当新增一条借阅记录时触发
        /// </summary>
        public event Action<BorrowRecord> OnBorrowRecordAdded;

        /// <summary>
        /// 当一条借阅记录被更新 (例如:归还) 时触发
        /// </summary>
        public event Action<BorrowRecord> OnBorrowRecordUpdated;

        /// <summary>
        /// 当库存信息发生变化时触发
        /// </summary>
        public event Action<InventoryData> OnInventoryChanged;

        /// <summary>
        /// 当收到新的失败告警时触发
        /// </summary>
        public event Action<FailureAlarmRecord> OnFailureAlarmReceived;

        #endregion

        #region Private Fields

        private readonly Dictionary<string, BorrowRecord> _borrowRecords = new Dictionary<string, BorrowRecord>();
        private readonly List<FailureAlarmRecord> _failureAlarms = new List<FailureAlarmRecord>();
        private InventoryData _inventory;

        #endregion

        #region Public Properties

        public IReadOnlyDictionary<string, BorrowRecord> BorrowRecords => _borrowRecords;
        public IReadOnlyList<FailureAlarmRecord> FailureAlarms => _failureAlarms;
        public InventoryData Inventory => _inventory;

        #endregion

        private DataCenter() { }

        #region Public Methods (Called by WebSocketManager)

        /// <summary>
        /// 应用初始化数据
        /// </summary>
        public void ApplyInit(InitDto dto)
        {
            // 1. 初始化库存
            _inventory = InventoryData.FromInitDto(dto);
            OnInventoryChanged?.Invoke(_inventory);

            // 2. 加载历史借还记录
            _borrowRecords.Clear();
            if (dto.history_records != null)
            {
                foreach (var historyDto in dto.history_records)
                {
                    var record = BorrowRecord.FromHistoryDto(historyDto);
                    _borrowRecords[record.RecordId] = record;
                }
            }

            // 3. 加载历史失败告警
            _failureAlarms.Clear();
            if (dto.alarm_history != null)
            {
                foreach (var alarmDto in dto.alarm_history)
                {
                    var alarm = FailureAlarmRecord.FromHistoryDto(alarmDto);
                    _failureAlarms.Add(alarm);
                }
            }

            // 4. 触发历史加载完成事件
            OnHistoryLoaded?.Invoke();
            Debug.Log("[DataCenter] Initial data applied. Loaded " + _borrowRecords.Count + " history records and " + _failureAlarms.Count + " alarms.");
        }

        /// <summary>
        /// 应用借出事件
        /// </summary>
        public void ApplyBorrow(BorrowEventDto dto)
        {
            if (_borrowRecords.ContainsKey(dto.record_id))
            {
                Debug.LogWarning($"[DataCenter] Duplicate borrow event received for record_id: {dto.record_id}. Ignoring.");
                return;
            }

            // 1. 创建并存储新的借还记录
            var newRecord = BorrowRecord.FromBorrowDto(dto);
            _borrowRecords[newRecord.RecordId] = newRecord;

            // 2. 更新库存
            _inventory.UpdateCurrentInventory(dto.current_inventory);

            // 3. 触发事件
            OnBorrowRecordAdded?.Invoke(newRecord);
            OnInventoryChanged?.Invoke(_inventory);
            Debug.Log($"[DataCenter] Borrow event applied for user: {dto.user}, record_id: {dto.record_id}");
        }

        /// <summary>
        /// 应用归还事件
        /// </summary>
        public void ApplyReturn(ReturnEventDto dto)
        {
            if (!_borrowRecords.TryGetValue(dto.record_id, out var recordToUpdate))
            {
                Debug.LogError($"[DataCenter] Return event received for an unknown record_id: {dto.record_id}. Ignoring.");
                return;
            }

            // 1. 更新领域模型
            recordToUpdate.ApplyReturn(dto.count, dto.time);

            // 2. 更新库存
            _inventory.UpdateCurrentInventory(dto.current_inventory);

            // 3. 触发事件
            OnBorrowRecordUpdated?.Invoke(recordToUpdate);
            OnInventoryChanged?.Invoke(_inventory);
            Debug.Log($"[DataCenter] Return event applied for record_id: {dto.record_id}");
        }

        /// <summary>
        /// 应用失败告警事件
        /// </summary>
        public void ApplyFailureAlarm(FailureAlarmDto dto)
        {
            var newAlarm = FailureAlarmRecord.FromDto(dto);
            _failureAlarms.Add(newAlarm);
            OnFailureAlarmReceived?.Invoke(newAlarm);
            Debug.Log($"[DataCenter] Failure alarm received: {dto.reason}");
        }

        #endregion
    }
}

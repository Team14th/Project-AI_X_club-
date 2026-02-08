using UnityEngine;

namespace ToolVisualization
{
    /// <summary>
    /// 应用根节点
    /// 负责初始化全局单例和管理应用生命周期
    /// </summary>
    public class AppRoot : MonoBehaviour
    {
        private void Awake()
        {
            Debug.Log("应用启动");

            // 先初始化 WebSocketManager（如果不存在）
            InitializeWebSocketManager();

            // DataCenter 是纯 C# 单例，访问 Instance 即可自动创建
            var dc = DataCenter.Instance;
            Debug.Log("[AppRoot] DataCenter 已初始化");

            Debug.Log("应用初始化完成");
        }

        private void InitializeWebSocketManager()
        {
            // 先在场景中查找是否已经存在
            var existing = FindObjectOfType<WebSocketManager>();
            if (existing != null)
            {
                Debug.Log("[AppRoot] WebSocketManager 已存在于场景中");
                return;
            }

            // 不存在则创建
            var go = new GameObject("WebSocketManager");
            go.AddComponent<WebSocketManager>();
            Debug.Log("[AppRoot] WebSocketManager 已创建");
        }

        private void Start()
        {
            // 订阅 DataCenter 事件 (示例)
            DataCenter.Instance.OnHistoryLoaded += OnHistoryLoaded;
            DataCenter.Instance.OnBorrowRecordAdded += OnBorrowRecordAdded;
            DataCenter.Instance.OnBorrowRecordUpdated += OnBorrowRecordUpdated;
            DataCenter.Instance.OnFailureAlarmReceived += OnFailureAlarmReceived;
            DataCenter.Instance.OnInventoryChanged += OnInventoryChanged;
        }

        private void OnDestroy()
        {
            // 取消订阅
            if (DataCenter.Instance != null)
            {
                DataCenter.Instance.OnHistoryLoaded -= OnHistoryLoaded;
                DataCenter.Instance.OnBorrowRecordAdded -= OnBorrowRecordAdded;
                DataCenter.Instance.OnBorrowRecordUpdated -= OnBorrowRecordUpdated;
                DataCenter.Instance.OnFailureAlarmReceived -= OnFailureAlarmReceived;
                DataCenter.Instance.OnInventoryChanged -= OnInventoryChanged;
            }
        }

        // ==================== 事件处理示例 ====================

        private void OnHistoryLoaded()
        {
            Debug.Log("[AppRoot] 历史数据加载完成");
        }

        private void OnBorrowRecordAdded(BorrowRecord record)
        {
            Debug.Log($"[AppRoot] 新增借出记录: {record.RecordId}, 用户: {record.User}");
        }

        private void OnBorrowRecordUpdated(BorrowRecord record)
        {
            Debug.Log($"[AppRoot] 借还记录已更新 (归还): {record.RecordId}");
        }

        private void OnFailureAlarmReceived(FailureAlarmRecord alarm)
        {
            Debug.Log($"[AppRoot] 新增失败报警: {alarm.AlarmId}, 原因: {alarm.Reason}");
        }

        private void OnInventoryChanged(InventoryData inventory)
        {
            Debug.Log($"[AppRoot] 库存已更新: {inventory.CurrentInventory}/{inventory.TotalInventory}");
        }
    }
}

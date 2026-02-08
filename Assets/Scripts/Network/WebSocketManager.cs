using System;
using System.Threading.Tasks;
using UnityEngine;
using NativeWebSocket;

namespace ToolVisualization
{
    /// <summary>
    /// WebSocket 管理器 (单例模式)
    /// 负责 WebSocket 连接、消息收发和分发
    /// </summary>
    public class WebSocketManager : MonoBehaviour
    {
        // 单例实例
        private static WebSocketManager _instance;
        public static WebSocketManager Instance
        {
            get
            {
                if (_instance == null)
                {
                    Debug.LogError("[WebSocketManager] 实例未初始化!");
                }
                return _instance;
            }
        }

        // WebSocket 连接对象
        private WebSocket _ws;

        // 后端地址 (可在 Inspector 中配置)
        [Header("WebSocket 配置")]
        [SerializeField] private string serverUrl = "ws://localhost:8000/ws";

        // ==================== 生命周期 ====================

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }

            _instance = this;
            DontDestroyOnLoad(gameObject);
            Debug.Log("[WebSocketManager] WebSocket 管理器已初始化");
        }

        private async void Start()
        {
            // 自动连接
            await Connect();
        }

        private void Update()
        {
            // 必须在主线程中调度 WebSocket 消息
#if !UNITY_WEBGL || UNITY_EDITOR
            if (_ws != null)
            {
                _ws.DispatchMessageQueue();
            }
#endif
        }

        private async void OnApplicationQuit()
        {
            await Disconnect();
        }

        // ==================== 连接管理 ====================

        /// <summary>
        /// 连接到后端 WebSocket 服务器
        /// </summary>
        public async Task Connect()
        {
            if (_ws != null && _ws.State == WebSocketState.Open)
            {
                Debug.LogWarning("[WebSocketManager] 已经连接,无需重复连接");
                return;
            }

            try
            {
                Debug.Log($"[WebSocketManager] 正在连接到 {serverUrl}...");

                _ws = new WebSocket(serverUrl);

                // 注册事件回调
                _ws.OnOpen += OnWebSocketOpen;
                _ws.OnMessage += OnWebSocketMessage;
                _ws.OnError += OnWebSocketError;
                _ws.OnClose += OnWebSocketClose;

                // 发起连接
                await _ws.Connect();
            }
            catch (Exception e)
            {
                Debug.LogError($"[WebSocketManager] 连接失败: {e.Message}");
            }
        }

        /// <summary>
        /// 断开连接
        /// </summary>
        public async Task Disconnect()
        {
            if (_ws != null)
            {
                await _ws.Close();
                _ws = null;
                Debug.Log("[WebSocketManager] 已断开连接");
            }
        }

        // ==================== WebSocket 事件回调 ====================

        private void OnWebSocketOpen()
        {
            Debug.Log("[WebSocketManager] WebSocket 连接已建立");
        }

        private void OnWebSocketMessage(byte[] data)
        {
            try
            {
                string json = System.Text.Encoding.UTF8.GetString(data);
                Debug.Log($"[WebSocketManager] 收到消息: {json}");

                // 解析消息基础结构
                var baseMsg = JsonUtility.FromJson<WsMessageDto>(json);

                // 根据类型分发消息
                DispatchMessage(baseMsg.type, baseMsg.payload);
            }
            catch (Exception e)
            {
                Debug.LogError($"[WebSocketManager] 解析消息失败: {e.Message}");
            }
        }

        private void OnWebSocketError(string errorMsg)
        {
            Debug.LogError($"[WebSocketManager] WebSocket 错误: {errorMsg}");
        }

        private void OnWebSocketClose(WebSocketCloseCode closeCode)
        {
            Debug.Log($"[WebSocketManager] WebSocket 连接已关闭: {closeCode}");

            // 可以在这里实现自动重连逻辑
            // Invoke("Connect", 5f);  // 5秒后重连
        }

        // ==================== 消息分发 ====================

        /// <summary>
        /// 根据消息类型分发到对应的处理函数
        /// </summary>
        private void DispatchMessage(string type, string payload)
        {
            switch (type)
            {
                case "init":
                    HandleInit(payload);
                    break;

                case "borrow":
                    HandleBorrow(payload);
                    break;

                case "return":
                    HandleReturn(payload);
                    break;

                case "failure_alarm":
                    HandleFailureAlarm(payload);
                    break;

                case "inventory_alarm":
                    HandleInventoryAlarm(payload);
                    break;

                default:
                    Debug.LogWarning($"[WebSocketManager] 未知消息类型: {type}");
                    break;
            }
        }

        // ==================== 消息处理函数 ====================

        private void HandleInit(string payload)
        {
            var dto = JsonUtility.FromJson<InitDto>(payload);
            Debug.Log($"[WebSocketManager] 收到初始化数据: 工具={dto.tool_name}, 库存={dto.current_inventory}/{dto.total_inventory}");

            // 分发到 DataCenter
            DataCenter.Instance.ApplyInit(dto);
        }

        private void HandleBorrow(string payload)
        {
            var dto = JsonUtility.FromJson<BorrowEventDto>(payload);
            Debug.Log($"[WebSocketManager] 收到借出事件: record_id={dto.record_id}, user={dto.user}");

            // 分发到 DataCenter
            DataCenter.Instance.ApplyBorrow(dto);
        }

        private void HandleReturn(string payload)
        {
            var dto = JsonUtility.FromJson<ReturnEventDto>(payload);
            Debug.Log($"[WebSocketManager] 收到归还事件: record_id={dto.record_id}");

            // 分发到 DataCenter
            DataCenter.Instance.ApplyReturn(dto);
        }

        private void HandleFailureAlarm(string payload)
        {
            var dto = JsonUtility.FromJson<FailureAlarmDto>(payload);
            Debug.Log($"[WebSocketManager] 收到失败报警: alarm_id={dto.alarm_id}, reason={dto.reason}");

            // 分发到 DataCenter
            DataCenter.Instance.ApplyFailureAlarm(dto);
        }

        private void HandleInventoryAlarm(string payload)
        {
            var dto = JsonUtility.FromJson<InventoryAlarmDto>(payload);
            Debug.Log($"[WebSocketManager] 收到库存告警: alarm_id={dto.alarm_id}, 当前库存={dto.current_inventory}");

            // 可以触发专门的库存告警事件，或者记录到日志
            // 这里暂时只打印日志
        }
    }
}

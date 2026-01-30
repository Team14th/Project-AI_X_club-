using NativeWebSocket;
using UnityEngine;
using System.Text;
using System.Threading.Tasks;

public class WebSocketManager : MonoBehaviour
{
    [Header("WebSocket Config")]
    public string serverUrl = "ws://localhost:8000/ws"; // FastAPI WebSocket URL

    private WebSocket ws;
    private bool isConnected = false;

    async void Start()
    {
        Debug.Log("WebSocketManager starting...");

        ws = new WebSocket(serverUrl);

        ws.OnOpen += () =>
        {
            Debug.Log("WebSocket connected");
            isConnected = true;
        };

        ws.OnMessage += (bytes) =>
        {
            string message = Encoding.UTF8.GetString(bytes);
            Debug.Log("WS Receive: " + message);
        };

        ws.OnError += (e) =>
        {
            Debug.LogError("WS Error: " + e);
        };

        ws.OnClose += (e) =>
        {
            Debug.LogWarning("WS Closed");
            isConnected = false;
        };

        // 连接服务器
        await ws.Connect();

        // 测试发送消息
        await SendMessageAfterConnected("{\"action\": \"get_tool_status\"}");
        await SendMessageAfterConnected("{\"action\": \"borrow_tool\", \"quantity\": 2}");
        await SendMessageAfterConnected("{\"action\": \"return_tool\", \"quantity\": 1}");
    }

    void Update()
    {
        ws?.DispatchMessageQueue();
    }

    /// <summary>
    /// 安全发送消息：确保连接完成后再发送
    /// </summary>
    public async Task SendMessageAfterConnected(string message)
    {
        // 等待连接完成
        int waitCount = 0;
        while (!isConnected)
        {
            await Task.Delay(100);
            waitCount++;
            if (waitCount > 50) // 超过5秒没连上
            {
                Debug.LogError("WebSocket failed to connect within 5 seconds.");
                return;
            }
        }

        try
        {
            await ws.SendText(message);
            Debug.Log("WS Send: " + message);
        }
        catch (System.Exception ex)
        {
            Debug.LogError("Send failed: " + ex.Message);
        }
    }

    private async void OnApplicationQuit()
    {
        if (ws != null)
        {
            await ws.Close();
        }
    }
}

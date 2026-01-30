using NativeWebSocket;
using UnityEngine;
using System.Text;

public class WebSocketManager : MonoBehaviour
{
    [Header("WebSocket Config")]
    public string serverUrl = "ws://localhost:8080";

    private WebSocket ws;

    async void Start()
    {
        Debug.Log("WebSocketManager starting...");

        ws = new WebSocket(serverUrl);

        ws.OnOpen += () =>
        {
            Debug.Log("WebSocket connected");
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
        };

        await ws.Connect();
    }

    void Update()
    {
        ws?.DispatchMessageQueue();
    }

    private async void OnApplicationQuit()
    {
        if (ws != null)
        {
            await ws.Close();
        }
    }
}

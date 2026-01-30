using UnityEngine;
using System.Threading.Tasks;

public class TestWSCalls : MonoBehaviour
{
    private WebSocketManager wsMgr;

    async void Start()
    {
        wsMgr = GameObject.Find("WebSocketManager").GetComponent<WebSocketManager>();

        // 异步发送消息，确保 WebSocket 已连接
        await wsMgr.SendMessageAfterConnected("{\"action\": \"get_tool_status\"}");
        await wsMgr.SendMessageAfterConnected("{\"action\": \"borrow_tool\", \"quantity\": 2}");
        await wsMgr.SendMessageAfterConnected("{\"action\": \"return_tool\", \"quantity\": 1}");
    }
}

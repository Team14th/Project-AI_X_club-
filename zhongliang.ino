
#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "HX711.h"

// ==================== 配置信息 ====================

// Wi-Fi 配置
const char* ssid = "FAST_E41F";
const char* password = "15538164127";

// 后端服务器配置
const char* websocket_host = "192.168.0.100";  // 修改为您的后端服务器 IP
const uint16_t websocket_port = 8000;
const char* websocket_path = "/ws";

// 设备标识
const char* device_id = "hardware_weight_001";

// HX711 引脚定义
const int LOADCELL_DOUT_PIN = 5;
const int LOADCELL_SCK_PIN = 6;

// LED 引脚定义
const int LED_PIN = 3;

// ==================== 全局变量 ====================

WebSocketsClient webSocket;
HX711 scale;

// 校准系数
float CALIBRATION_FACTOR = 219.3;

// 物品配置
const float SINGLE_ITEM_WEIGHT = 20.0;    // 单个物品重量（20克）
const int ALARM_THRESHOLD = 3;            // 报警阈值：数量≤3时报警
const float MIN_DETECTION_WEIGHT = 5.0;   // 最小检测重量

// 状态变量
int currentItemCount = 0;
int lastStableItemCount = 0;
float lastWeight = 0;

// 状态检测变量
unsigned long stateChangeTime = 0;
const unsigned long DEBOUNCE_TIME = 500;  // 状态稳定时间
unsigned long lastDisplayTime = 0;

// WebSocket 状态
bool isIdentified = false;
String last_record_id = "";

// 事件统计
unsigned long eventCount = 0;
unsigned long borrowCount = 0;
unsigned long returnCount = 0;

// ==================== WebSocket 事件处理 ====================

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch(type) {
        case WStype_DISCONNECTED:
            Serial.println("\n[WebSocket] ✗ 已断开连接!");
            isIdentified = false;
            break;

        case WStype_CONNECTED:
            Serial.println("\n[WebSocket] ✓ 已连接到服务器");
            sendIdentifyMessage();
            break;

        case WStype_TEXT:
            Serial.printf("\n[WebSocket] ← 收到: %s\n", payload);
            handleIncomingMessage((char*)payload);
            break;

        case WStype_ERROR:
            Serial.println("\n[WebSocket] ✗ 连接错误");
            break;

        default:
            break;
    }
}

// ==================== 消息处理与发送 ====================

void sendIdentifyMessage() {
    StaticJsonDocument<200> doc;
    doc["type"] = "identify";
    doc["role"] = "hardware";
    doc["device_id"] = device_id;

    String json_output;
    serializeJson(doc, json_output);

    Serial.printf("[WebSocket] → 发送身份识别: %s\n", json_output.c_str());
    
    webSocket.sendTXT(json_output);
}

void sendBorrowEvent(int count) {
    if (!isIdentified) {
        Serial.println("[错误] 尚未完成身份识别,无法发送事件");
        return;
    }

    StaticJsonDocument<200> doc;
    doc["type"] = "hardware_event";
    doc["event"] = "borrow";
    doc["count"] = count;

    String json_output;
    serializeJson(doc, json_output);

    Serial.printf("[WebSocket] → 发送借出事件: count=%d\n", count);
    
    webSocket.sendTXT(json_output);
    
    borrowCount++;
    eventCount++;
}

void sendReturnEvent(int count) {
    if (!isIdentified) {
        Serial.println("[错误] 尚未完成身份识别,无法发送事件");
        return;
    }

    if (last_record_id.length() == 0) {
        Serial.println("[错误] 没有可用的 record_id 来归还!");
        return;
    }

    StaticJsonDocument<200> doc;
    doc["type"] = "hardware_event";
    doc["event"] = "return";
    doc["record_id"] = last_record_id;
    doc["count"] = count;

    String json_output;
    serializeJson(doc, json_output);

    Serial.printf("[WebSocket] → 发送归还事件: record_id=%s, count=%d\n", 
                    last_record_id.c_str(), count);
    
    webSocket.sendTXT(json_output);
    
    returnCount++;
    eventCount++;
}

void handleIncomingMessage(char* json_payload) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, json_payload);

    if (error) {
        Serial.print(F("[错误] JSON 解析失败: "));
        Serial.println(error.c_str());
        return;
    }

    const char* type = doc["type"];

    if (strcmp(type, "identify_ack") == 0) {
        const char* status = doc["status"];
        if (strcmp(status, "ok") == 0) {
            isIdentified = true;
            Serial.println("[WebSocket] ✓ 身份识别成功!");
        }
    } 
    else if (strcmp(type, "hardware_response") == 0) {
        const char* event = doc["event"];
        const char* status = doc["status"];

        if (strcmp(event, "borrow") == 0 && strcmp(status, "ok") == 0) {
            last_record_id = doc["record_id"].as<String>();
            Serial.printf("[WebSocket] ✓ 借出成功! record_id: %s\n", last_record_id.c_str());
        }
        else if (strcmp(event, "return") == 0 && strcmp(status, "ok") == 0) {
            Serial.println("[WebSocket] ✓ 归还成功!");
            last_record_id = "";
        }
    } 
    else if (strcmp(type, "error") == 0) {
        const char* message = doc["message"];
        Serial.printf("[WebSocket] ✗ 错误: %s\n", message);
    }
}

// ==================== 重量检测逻辑 ====================

float getStableWeight() {
  // 读取3次取平均值
  float weight = scale.get_units(3);
  
  // 处理负值：小负值设为0
  if (weight < 0 && weight > -3.0) {
    weight = 0;
  }
  
  return weight;
}

int calculateItemCount(float weight) {
  // 如果重量小于最小检测重量，返回0
  if (weight < MIN_DETECTION_WEIGHT) {
    return 0;
  }
  
  // 简单计算：重量除以单个物品重量
  float exactCount = weight / SINGLE_ITEM_WEIGHT;
  
  // 四舍五入到最接近的整数
  int itemCount = round(exactCount);
  
  // 确保不为负数
  if (itemCount < 0) {
    itemCount = 0;
  }
  
  return itemCount;
}

void updateLED(int itemCount) {
  // 数量≤3时点亮，>3时熄灭
  if (itemCount <= ALARM_THRESHOLD) {
    digitalWrite(LED_PIN, HIGH);  // 点亮
  } else {
    digitalWrite(LED_PIN, LOW);   // 熄灭
  }
}

// ==================== 状态变化检测和上报 ====================

void checkStateChange() {
  // 获取当前时间
  unsigned long currentTime = millis();
  
  // 获取当前重量和计算数量
  float weight = getStableWeight();
  int itemCount = calculateItemCount(weight);
  
  // 如果数量变化了
  if (itemCount != currentItemCount) {
    // 记录变化时间
    if (stateChangeTime == 0) {
      stateChangeTime = currentTime;
    }
    
    // 如果状态稳定了一段时间
    if (currentTime - stateChangeTime >= DEBOUNCE_TIME) {
      // 计算变化数量
      int change = itemCount - lastStableItemCount;
      
      // 显示状态变化
      Serial.println("----------------------------------------");
      if (change > 0) {
        Serial.print("放入物品: +");
        Serial.print(change);
        Serial.print("个 (总数: ");
        Serial.print(itemCount);
        Serial.println(")");
        
        // 上报归还事件
        Serial.println(">>> 触发: 归还事件");
        sendReturnEvent(change);
      } else if (change < 0) {
        Serial.print("取出物品: ");
        Serial.print(change);
        Serial.print("个 (总数: ");
        Serial.print(itemCount);
        Serial.println(")");
        
        // 上报借出事件
        Serial.println(">>> 触发: 借出事件");
        sendBorrowEvent(abs(change));
      }
      
      // 更新稳定状态
      lastStableItemCount = itemCount;
      currentItemCount = itemCount;
      lastWeight = weight;
      
      // 更新LED
      updateLED(currentItemCount);
      
      // 显示当前状态
      Serial.print("当前状态: 重量=");
      Serial.print(weight, 1);
      Serial.print("g, 数量=");
      Serial.println(itemCount);
      Serial.println("----------------------------------------");
      
      // 重置变化时间
      stateChangeTime = 0;
    }
  } else {
    // 状态没有变化，重置计时器
    stateChangeTime = 0;
    lastWeight = weight;
  }
}

// ==================== 串口命令处理 ====================

void handleSerialCommand() {
  if (Serial.available()) {
    char command = Serial.read();
    
    switch (command) {
      case 't':
      case 'T':
        Serial.println("执行去皮...");
        scale.tare();
        currentItemCount = 0;
        lastStableItemCount = 0;
        lastWeight = 0;
        stateChangeTime = 0;
        Serial.println("去皮完成");
        break;
        
      case 'r':
      case 'R':
        Serial.println("重置状态...");
        currentItemCount = 0;
        lastStableItemCount = 0;
        lastWeight = 0;
        stateChangeTime = 0;
        updateLED(currentItemCount);
        Serial.println("状态已重置");
        break;
        
      case 'l':
      case 'L':
        Serial.println("LED测试: 点亮3秒");
        digitalWrite(LED_PIN, HIGH);
        delay(3000);
        updateLED(currentItemCount);  // 恢复原状态
        Serial.println("LED测试完成");
        break;
        
      case 's':
      case 'S':
        Serial.println("系统状态:");
        Serial.print("  当前重量: ");
        Serial.print(lastWeight, 1);
        Serial.println(" 克");
        Serial.print("  当前数量: ");
        Serial.println(currentItemCount);
        Serial.print("  报警阈值: ");
        Serial.println(ALARM_THRESHOLD);
        Serial.print("  LED状态: ");
        Serial.println(digitalRead(LED_PIN) == HIGH ? "点亮" : "熄灭");
        Serial.print("  WebSocket状态: ");
        Serial.println(isIdentified ? "已连接" : "未连接");
        if (last_record_id.length() > 0) {
          Serial.print("  最后record_id: ");
          Serial.println(last_record_id);
        }
        Serial.print("  事件统计 - 总事件: ");
        Serial.print(eventCount);
        Serial.print(", 借出: ");
        Serial.print(borrowCount);
        Serial.print(", 归还: ");
        Serial.println(returnCount);
        break;
        
      case 'h':
      case 'H':
        Serial.println("可用命令:");
        Serial.println("  t/T - 去皮(清零)");
        Serial.println("  r/R - 重置状态");
        Serial.println("  l/L - LED测试");
        Serial.println("  s/S - 系统状态");
        Serial.println("  h/H - 帮助");
        break;
    }
  }
}

// ==================== Arduino 主程序 ====================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("========================================");
  Serial.println("      ESP32-S3 智能物品检测系统");
  Serial.println("========================================");
  
  // 初始化LED引脚
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);  // 初始状态点亮
  
  Serial.println("系统功能:");
  Serial.println("  1. 检测重量和物品数量");
  Serial.println("  2. 检测放入/取出状态");
  Serial.println("  3. 数量≤3时LED报警点亮");
  Serial.println("  4. WebSocket上报借出/归还事件");
  Serial.println("========================================");
  
  // 初始化HX711
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_scale(CALIBRATION_FACTOR);
  scale.tare();
  
  // 连接Wi-Fi
  Serial.printf("\n正在连接到 Wi-Fi: %s\n", ssid);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ Wi-Fi 已连接!");
    Serial.print("IP 地址: ");
    Serial.println(WiFi.localIP());
    
    // 配置WebSocket
    webSocket.begin(websocket_host, websocket_port, websocket_path);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
    Serial.println("✓ WebSocket 已配置");
  } else {
    Serial.println("\n✗ Wi-Fi 连接失败!");
    Serial.println("将以离线模式运行");
  }
  
  Serial.println("系统初始化完成，开始检测...");
  Serial.println();
}

void loop() {
  // 处理WebSocket消息
  webSocket.loop();
  
  // 检查传感器是否就绪
  if (scale.wait_ready_timeout(500)) {
    // 检测状态变化
    checkStateChange();
    
    // 每秒显示一次当前状态
    unsigned long currentTime = millis();
    if (currentTime - lastDisplayTime >= 1000) {
      float currentWeight = getStableWeight();
      Serial.print("重量: ");
      Serial.print(currentWeight, 1);
      Serial.print("g | 数量: ");
      Serial.print(currentItemCount);
      Serial.print(" | LED: ");
      Serial.print(digitalRead(LED_PIN) == HIGH ? "点亮" : "熄灭");
      Serial.print(" | 状态: ");
      
      if (currentItemCount <= ALARM_THRESHOLD) {
        Serial.print("报警");
      } else {
        Serial.print("正常");
      }
      
      // 显示WebSocket连接状态
      Serial.print(" | WS: ");
      Serial.println(isIdentified ? "已连接" : "未连接");
      
      lastDisplayTime = currentTime;
    }
    
    delay(200);  // 控制检测频率
    
  } else {
    Serial.println("传感器未响应，检查连接...");
    delay(1000);
  }
  
  // 处理串口命令
  handleSerialCommand();
}
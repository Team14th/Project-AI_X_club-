#include <Arduino.h>
#include "HX711.h"

// HX711引脚定义
const int LOADCELL_DOUT_PIN = 5;
const int LOADCELL_SCK_PIN = 6;

// LED引脚定义
const int LED_PIN = 3;  // 将LED连接到GPIO3

// HX711对象
HX711 scale;

// 校准系数（替换为你校准得到的值）
const float CALIBRATION_FACTOR = 219.3;

// 重量阈值设置
const float MIN_DETECTION_WEIGHT = 5.0;
const float ONE_ITEM_MIN = 100.0;
const float ONE_ITEM_MAX = 200.0;
const float TWO_ITEMS_THRESHOLD = 200.0;

// 状态变量
enum ItemState {
  STATE_NO_ITEM,
  STATE_ONE_ITEM,
  STATE_TWO_ITEMS
};

ItemState currentState = STATE_NO_ITEM;
ItemState previousState = STATE_NO_ITEM;

// 去抖和滤波变量
const unsigned long DEBOUNCE_TIME = 800;
const int SMOOTHING_SAMPLES = 8;
float weightBuffer[SMOOTHING_SAMPLES];
int bufferIndex = 0;
unsigned long stateChangeTime = 0;
unsigned long lastDisplayTime = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // 初始化LED引脚
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  
  Serial.println("========================================");
  Serial.println("      ESP32-S3 智能物品检测系统");
  Serial.println("========================================");
  Serial.println("检测规则：");
  Serial.println("  100-200克: 一个物品 (LED熄灭)");
  Serial.println("  >200克:    两个物品 (LED熄灭)");
  Serial.println("  <100克:    无物品 (LED点亮)");
  Serial.println("========================================");
  
  // 初始化HX711
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_scale(CALIBRATION_FACTOR);
  scale.tare();
  
  Serial.print("校准系数: ");
  Serial.println(CALIBRATION_FACTOR);
  Serial.print("LED引脚: GPIO");
  Serial.println(LED_PIN);
  Serial.println("系统就绪，开始检测...");
  Serial.println();
  
  // 初始化重量缓冲区
  for (int i = 0; i < SMOOTHING_SAMPLES; i++) {
    weightBuffer[i] = 0;
  }
}

// 获取平滑后的重量
float getSmoothedWeight() {
  float rawWeight = scale.get_units(3);
  weightBuffer[bufferIndex] = rawWeight;
  bufferIndex = (bufferIndex + 1) % SMOOTHING_SAMPLES;
  
  float sum = 0;
  for (int i = 0; i < SMOOTHING_SAMPLES; i++) {
    sum += weightBuffer[i];
  }
  return sum / SMOOTHING_SAMPLES;
}

// 判断物品状态
ItemState determineState(float weight) {
  if (weight < MIN_DETECTION_WEIGHT) {
    return STATE_NO_ITEM;
  } else if (weight >= ONE_ITEM_MIN && weight <= ONE_ITEM_MAX) {
    return STATE_ONE_ITEM;
  } else if (weight > TWO_ITEMS_THRESHOLD) {
    return STATE_TWO_ITEMS;
  } else {
    return currentState;
  }
}

// 控制LED灯（修改后的逻辑：无物品时点亮，有物品时熄灭）
void controlLED(ItemState state) {
  if (state == STATE_NO_ITEM) {
    digitalWrite(LED_PIN, HIGH);  // 无物品时点亮LED
  } else {
    digitalWrite(LED_PIN, LOW);   // 有物品时熄灭LED
  }
}

// 显示重量信息
void displayWeightInfo(float weight) {
  unsigned long currentTime = millis();
  
  // 每秒显示一次重量信息
  if (currentTime - lastDisplayTime >= 1000) {
    Serial.print("时间: ");
    Serial.print(currentTime / 1000);
    Serial.print("s | 重量: ");
    Serial.print(weight, 1);
    Serial.print(" 克");
    
    // 显示重量区间指示
    if (weight < ONE_ITEM_MIN) {
      Serial.print(" [无物品]");
    } else if (weight <= ONE_ITEM_MAX) {
      Serial.print(" [单物品区间]");
    } else {
      Serial.print(" [多物品区间]");
    }
    
    // 显示LED状态
    Serial.print(" | LED: ");
    Serial.println(digitalRead(LED_PIN) == HIGH ? "点亮" : "熄灭");
    
    lastDisplayTime = currentTime;
  }
}

// 显示状态变化
void displayStateChange(ItemState newState) {
  unsigned long currentTime = millis();
  
  // 检查状态是否稳定足够长时间
  if (newState != previousState) {
    stateChangeTime = currentTime;
    previousState = newState;
    return;
  }
  
  // 状态已稳定超过去抖时间
  if (currentTime - stateChangeTime >= DEBOUNCE_TIME && currentState != newState) {
    // 显示变化动作
    Serial.println("----------------------------------------");
    
    if (currentState == STATE_TWO_ITEMS && newState == STATE_ONE_ITEM) {
      Serial.println("动作: 取走一个物品");
    } else if (currentState == STATE_ONE_ITEM && newState == STATE_NO_ITEM) {
      Serial.println("动作: 取走一个物品");
    } else if (currentState == STATE_NO_ITEM && newState == STATE_ONE_ITEM) {
      Serial.println("动作: 放入一个物品");
    } else if (currentState == STATE_ONE_ITEM && newState == STATE_TWO_ITEMS) {
      Serial.println("动作: 放入一个物品");
    }
    
    // 更新状态并显示
    currentState = newState;
    
    switch (currentState) {
      case STATE_NO_ITEM:
        Serial.println("当前状态: 无物品");
        break;
      case STATE_ONE_ITEM:
        Serial.println("当前状态: 一个物品");
        break;
      case STATE_TWO_ITEMS:
        Serial.println("当前状态: 两个物品");
        break;
    }
    
    Serial.println("----------------------------------------");
    Serial.println();
    
    // 更新LED状态
    controlLED(currentState);
  }
}

// LED测试模式
void ledTestMode() {
  Serial.println("LED测试模式开始...");
  
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("LED点亮");
    delay(500);
    digitalWrite(LED_PIN, LOW);
    Serial.println("LED熄灭");
    delay(500);
  }
  
  Serial.println("LED测试模式结束");
}

void loop() {
  // 检查HX711是否就绪
  if (scale.wait_ready_timeout(500)) {
    // 获取平滑后的重量
    float currentWeight = getSmoothedWeight();
    
    // 显示重量信息
    displayWeightInfo(currentWeight);
    
    // 判断状态
    ItemState newState = determineState(currentWeight);
    
    // 显示状态变化
    displayStateChange(newState);
    
    delay(100);
  } else {
    Serial.println("传感器未响应，检查连接...");
    delay(1000);
  }
  
  // 处理串口命令
  if (Serial.available()) {
    char command = Serial.read();
    
    switch (command) {
      case 't':
      case 'T':
        Serial.println("执行去皮...");
        scale.tare();
        for (int i = 0; i < SMOOTHING_SAMPLES; i++) {
          weightBuffer[i] = 0;
        }
        Serial.println("去皮完成");
        break;
        
      case 'r':
      case 'R':
        Serial.println("重置状态...");
        currentState = STATE_NO_ITEM;
        previousState = STATE_NO_ITEM;
        stateChangeTime = millis();
        controlLED(currentState);
        Serial.println("状态已重置");
        break;
        
      case 'l':
      case 'L':
        ledTestMode();
        break;
        
      case 'h':
      case 'H':
        Serial.println("可用命令:");
        Serial.println("  t/T - 去皮(清零)");
        Serial.println("  r/R - 重置状态");
        Serial.println("  l/L - LED测试");
        Serial.println("  h/H - 显示帮助");
        break;
    }
  }
}
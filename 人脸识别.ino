#include "esp_camera.h"
#include <ESP32Servo.h>

// ========================= 硬件配置 =========================
Servo myServo;
#define SERVO_PIN 2        // 舵机控制引脚
#define BUZZER_PIN 1       // 蜂鸣器控制引脚

// XIAO ESP32S3 Sense 摄像头引脚配置
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     10
#define SIOD_GPIO_NUM     40
#define SIOC_GPIO_NUM     39
#define Y9_GPIO_NUM       48
#define Y8_GPIO_NUM       11
#define Y7_GPIO_NUM       12
#define Y6_GPIO_NUM       14
#define Y5_GPIO_NUM       16
#define Y4_GPIO_NUM       18
#define Y3_GPIO_NUM       17
#define Y2_GPIO_NUM       15
#define VSYNC_GPIO_NUM    38
#define HREF_GPIO_NUM     47
#define PCLK_GPIO_NUM     13

// ========================= 系统配置 =========================
#define DETECT_INTERVAL   1000     // 检测间隔（毫秒）
#define DOOR_OPEN_TIME    3000     // 开门持续时间（毫秒）

// 系统状态
bool systemRunning = false;        // 系统是否运行
bool doorOpen = false;             // 门是否打开
unsigned long lastDetectTime = 0;
unsigned long doorOpenStartTime = 0;

// ========================= 蜂鸣器控制 =========================
void beepFail() {
  // 检测失败提示音：短促一声（低电平触发）
  digitalWrite(BUZZER_PIN, LOW);  // LOW 触发蜂鸣器
  delay(50);
  digitalWrite(BUZZER_PIN, HIGH); // HIGH 关闭蜂鸣器
}

// ========================= 舵机控制 =========================
void openDoor() {
  if (!doorOpen) {
    Serial.println("🚪 检测到人脸，开门！");
    myServo.write(90);  // 舵机旋转90度
    doorOpen = true;
    doorOpenStartTime = millis();
    // 注意：检测到人脸时不再让蜂鸣器响
  }
}

void closeDoor() {
  if (doorOpen) {
    Serial.println("🚪 关门！");
    myServo.write(0);   // 舵机回到0度
    doorOpen = false;
  }
}

// ========================= 摄像头控制 =========================
bool initCamera() {
  Serial.println("初始化摄像头...");
  
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.xclk_freq_hz = 10000000;       // 10MHz时钟
  config.pixel_format = PIXFORMAT_GRAYSCALE;  // 灰度图像
  config.frame_size = FRAMESIZE_QQVGA;  // 160x120像素
  config.jpeg_quality = 12;
  config.fb_count = 1;
  config.fb_location = CAMERA_FB_IN_DRAM;
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("摄像头初始化失败！错误代码: 0x%x\n", err);
    return false;
  }
  
  delay(500);  // 等待摄像头稳定
  Serial.println("摄像头初始化成功！");
  return true;
}

// ========================= 人脸检测函数 =========================
bool detectFace(camera_fb_t* fb) {
  if (!fb || fb->len == 0) return false;
  
  int width = fb->width;
  int height = fb->height;
  
  // 1. 计算图像中心区域的平均亮度（人脸通常在这里）
  int centerStartX = width / 4;
  int centerEndX = width * 3 / 4;
  int centerStartY = height / 4;
  int centerEndY = height * 3 / 4;
  
  long centerSum = 0;
  int centerCount = 0;
  
  for (int y = centerStartY; y < centerEndY; y += 2) {
    for (int x = centerStartX; x < centerEndX; x += 2) {
      int idx = y * width + x;
      if (idx < fb->len) {
        centerSum += fb->buf[idx];
        centerCount++;
      }
    }
  }
  
  if (centerCount == 0) return false;
  float centerAvg = (float)centerSum / centerCount;
  
  // 2. 计算图像边缘区域的平均亮度
  long edgeSum = 0;
  int edgeCount = 0;
  
  // 采样图像边缘的像素
  for (int x = 10; x < width - 10; x += 5) {
    // 上边缘
    int idx1 = 10 * width + x;
    // 下边缘
    int idx2 = (height - 10) * width + x;
    
    if (idx1 < fb->len) {
      edgeSum += fb->buf[idx1];
      edgeCount++;
    }
    if (idx2 < fb->len) {
      edgeSum += fb->buf[idx2];
      edgeCount++;
    }
  }
  
  if (edgeCount == 0) return false;
  float edgeAvg = (float)edgeSum / edgeCount;
  
  // 3. 计算亮度差异
  float brightnessDiff = abs(centerAvg - edgeAvg);
  
  // 4. 打印调试信息（可选）
  static int debugCounter = 0;
  if (debugCounter++ % 10 == 0) {  // 每10次打印一次
    Serial.printf("中心亮度: %.1f, 边缘亮度: %.1f, 差异: %.1f\n", 
                  centerAvg, edgeAvg, brightnessDiff);
  }
  
  // 5. 判断是否有人脸（中心与边缘亮度差异大）
  // 你可以调整这个阈值来改变检测灵敏度
  return (brightnessDiff > 25);  // 阈值25，可根据实际情况调整
}

// ========================= 系统控制函数 =========================
void startSystem() {
  if (systemRunning) {
    Serial.println("系统已经在运行中");
    return;
  }
  
  if (!initCamera()) {
    Serial.println("无法启动系统：摄像头初始化失败");
    return;
  }
  
  systemRunning = true;
  lastDetectTime = 0;  // 立即开始检测
  
  Serial.println("✅ 系统已启动");
  Serial.println("正在检测人脸...");
  Serial.println("检测到人脸将自动开门");
  Serial.println("输入 'stop' 停止系统");
}

void stopSystem() {
  if (!systemRunning) {
    Serial.println("系统未运行");
    return;
  }
  
  systemRunning = false;
  
  // 关闭门
  closeDoor();
  
  // 关闭蜂鸣器（确保不会响）对于低电平触发，设置为 HIGH
  digitalWrite(BUZZER_PIN, HIGH);
  
  // 注意：ESP32摄像头库没有直接的关闭函数
  // 但我们可以通过停止读取来"关闭"它
  Serial.println("🛑 系统已停止");
}

// ========================= 主检测循环 =========================
void checkForFace() {
  if (!systemRunning) return;
  
  // 获取摄像头图像
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("获取图像失败");
    return;
  }
  
  // 检测人脸
  if (detectFace(fb)) {
    Serial.println("✅ 检测到人脸！");
    openDoor();
  } else {
    Serial.println("👤 未检测到人脸");
    // 只有检测失败时才发出蜂鸣器声音
    beepFail();
  }
  
  // 释放图像缓冲区
  esp_camera_fb_return(fb);
}

// ========================= 初始化函数 =========================
void setup() {
  Serial.begin(115200);
  delay(1000);  // 等待串口稳定
  
  Serial.println("========================================");
  Serial.println("    人脸检测舵机控制系统");
  Serial.println("========================================");
  Serial.println("");
  Serial.println("功能说明：");
  Serial.println("1. 检测到人脸 → 舵机旋转90度");
  Serial.println("2. 检测失败 → 蜂鸣器提示");
  Serial.println("3. 开门3秒后自动关闭");
  Serial.println("");
  Serial.println("串口指令：");
  Serial.println("  start - 启动系统");
  Serial.println("  stop  - 停止系统");
  Serial.println("  test  - 测试硬件");
  Serial.println("  help  - 显示帮助");
  Serial.println("========================================");
  
  // 初始化舵机
  myServo.attach(SERVO_PIN);
  myServo.write(0);  // 初始位置：关门
  
  // 初始化蜂鸣器（低电平触发）
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, HIGH);  // 设置为 HIGH 不响
  
  // 启动提示音（低电平触发）
  for (int i = 0; i < 2; i++) {
    digitalWrite(BUZZER_PIN, LOW);   // LOW 触发蜂鸣器响
    delay(100);
    digitalWrite(BUZZER_PIN, HIGH);  // HIGH 关闭蜂鸣器
    delay(100);
  }
  
  Serial.println("系统初始化完成！");
  Serial.println("请输入 'start' 启动系统");
}

// ========================= 主循环函数 =========================
void loop() {
  // 1. 处理串口指令
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.equalsIgnoreCase("start")) {
      startSystem();
    } 
    else if (command.equalsIgnoreCase("stop")) {
      stopSystem();
    }
    else if (command.equalsIgnoreCase("test")) {
      testHardware();
    }
    else if (command.equalsIgnoreCase("help")) {
      showHelp();
    }
  }
  
  // 2. 自动关门（如果门已打开超过指定时间）
  if (doorOpen && (millis() - doorOpenStartTime > DOOR_OPEN_TIME)) {
    closeDoor();
  }
  
  // 3. 定期检测人脸
  if (systemRunning && (millis() - lastDetectTime > DETECT_INTERVAL)) {
    lastDetectTime = millis();
    checkForFace();
  }
  
  // 短暂延迟，避免CPU占用过高
  delay(10);
}

// ========================= 辅助函数 =========================
void testHardware() {
  Serial.println("=== 硬件测试 ===");
  
  // 测试舵机
  Serial.println("测试舵机...");
  myServo.write(0);
  delay(500);
  myServo.write(90);
  delay(1000);
  myServo.write(0);
  delay(500);
  Serial.println("舵机测试完成 ✓");
  
  // 测试蜂鸣器（低电平触发）
  Serial.println("测试蜂鸣器...");
  digitalWrite(BUZZER_PIN, LOW);   // 响
  delay(200);
  digitalWrite(BUZZER_PIN, HIGH);  // 不响
  Serial.println("蜂鸣器测试完成 ✓");
  
  // 测试摄像头
  Serial.println("测试摄像头...");
  if (initCamera()) {
    // 尝试获取一帧图像
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) {
      Serial.printf("摄像头测试成功！\n");
      Serial.printf("  图像大小: %d字节\n", fb->len);
      Serial.printf("  分辨率: %d x %d\n", fb->width, fb->height);
      
      // 简单检测测试
      if (detectFace(fb)) {
        Serial.println("  检测到人脸");
      } else {
        Serial.println("  未检测到人脸");
      }
      
      esp_camera_fb_return(fb);
    } else {
      Serial.println("  获取图像失败");
    }
  }
  
  // 如果系统不在运行状态，不保持摄像头开启
  if (!systemRunning) {
    // ESP32摄像头库没有关闭函数，但我们会停止使用它
    Serial.println("摄像头测试完成");
  }
  
  Serial.println("=== 硬件测试完成 ===");
}

void showHelp() {
  Serial.println("=== 系统帮助 ===");
  Serial.println("指令列表:");
  Serial.println("  start - 启动人脸检测系统");
  Serial.println("  stop  - 停止系统");
  Serial.println("  test  - 测试所有硬件");
  Serial.println("  help  - 显示此帮助");
  
  Serial.println("\n系统行为:");
  Serial.println("1. 启动后，每1秒检测一次人脸");
  Serial.println("2. 检测到人脸 → 舵机旋转90度");
  Serial.println("3. 检测失败 → 蜂鸣器短促提示");
  Serial.println("4. 开门3秒后自动关闭");
  
  Serial.println("\n检测灵敏度调整:");
  Serial.println("在代码中修改阈值:");
  Serial.println("  打开门限: brightnessDiff > 25");
  Serial.println("  增大数字 → 更严格，减小数字 → 更灵敏");
  
  Serial.println("\n硬件连接确认:");
  Serial.println("  舵机: 引脚2");
  Serial.println("  蜂鸣器: 引脚1（低电平触发）");
  Serial.println("  摄像头: 已连接在XIAO Sense板上");
}
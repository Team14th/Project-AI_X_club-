using TMPro;
using UnityEngine;
using UnityEngine.UI;
using System.Collections;

namespace ToolVisualization
{
    public class BorrowRecordItem : MonoBehaviour
    {
        [Header("Left Info")]
        public TMP_Text nameValueText;
        public TMP_Text borrowCountValueText;
        public TMP_Text startTimeValueText;

        [Header("Right Info")]
        public TMP_Text returnCountValueText;
        public TMP_Text endTimeValueText;

        [Header("Progress")]
        public Image progressFill;

        [Header("Colors")]
        public Color borrowingColor = new Color(0.3f, 0.6f, 1f); // 蓝色
        public Color returnedColor = new Color(0.3f, 1f, 0.6f);  // 绿色

        private Coroutine progressCoroutine;

        // ================= 初始化（借用发生） =================
        public void Init(string userName, int borrowCount, string startTime)
        {
            nameValueText.text = userName;
            borrowCountValueText.text = borrowCount.ToString();
            startTimeValueText.text = startTime;

            returnCountValueText.text = "未归还";
            endTimeValueText.text = "未归还";

            progressFill.color = borrowingColor;

            SetProgressImmediate(0f);
            AnimateProgressTo(0.5f, 0.5f); // 0 → 0.5（0.5秒）
        }

        // ================= 归还发生 =================
        public void SetReturned(int returnCount, string endTime)
        {
            returnCountValueText.text = returnCount.ToString();
            endTimeValueText.text = endTime;

            progressFill.color = returnedColor;

            AnimateProgressTo(1f, 0.4f); // 当前 → 1
        }

        // ================= 核心动画方法 =================
        private void AnimateProgressTo(float target, float duration)
        {
            if (progressCoroutine != null)
                StopCoroutine(progressCoroutine);

            progressCoroutine = StartCoroutine(ProgressAnimation(target, duration));
        }

        private IEnumerator ProgressAnimation(float target, float duration)
        {
            float start = progressFill.fillAmount;
            float time = 0f;

            while (time < duration)
            {
                time += Time.deltaTime;
                float t = time / duration;
                progressFill.fillAmount = Mathf.Lerp(start, target, t);
                yield return null;
            }

            progressFill.fillAmount = target;
        }

        private void SetProgressImmediate(float value)
        {
            if (progressCoroutine != null)
                StopCoroutine(progressCoroutine);

            progressFill.fillAmount = value;
        }
    }
}

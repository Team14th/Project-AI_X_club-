using UnityEngine;
using TMPro;
using System.Collections;

public class BeijingDateTimeUI : MonoBehaviour
{
    private TextMeshProUGUI text;

    void Awake()
    {
        text = GetComponent<TextMeshProUGUI>();
    }

    void OnEnable()
    {
        StartCoroutine(UpdateTime());
    }

    void OnDisable()
    {
        StopAllCoroutines();
    }

    IEnumerator UpdateTime()
    {
        while (true)
        {
            text.text = BeijingTime.Now.ToString("yyyy-M-d HH:mm:ss");
            yield return new WaitForSeconds(1f);
        }
    }
}

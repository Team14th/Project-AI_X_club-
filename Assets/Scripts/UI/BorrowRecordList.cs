using UnityEngine;
using System.Collections.Generic;

namespace ToolVisualization
{
    public class BorrowRecordList : MonoBehaviour
    {
        [Header("UI")]
        public BorrowRecordItem itemPrefab;
        public Transform contentRoot;

        // recordId -> UI Item
        private Dictionary<string, BorrowRecordItem> recordMap =
            new Dictionary<string, BorrowRecordItem>();

        private DataCenter dataCenter;

        void Awake()
        {
            // 尽量早缓存引用，避免反复访问 Instance
            dataCenter = DataCenter.Instance;
        }

        void OnEnable()
        {
            if (dataCenter == null)
                return;

            dataCenter.OnBorrowRecordAdded += OnRecordAdded;
            dataCenter.OnBorrowRecordUpdated += OnRecordUpdated;
        }

        void OnDisable()
        {
            // ⚠️ 关键防御：退出 Play / 场景卸载时 DataCenter 可能已不存在
            if (dataCenter == null)
                return;

            dataCenter.OnBorrowRecordAdded -= OnRecordAdded;
            dataCenter.OnBorrowRecordUpdated -= OnRecordUpdated;
        }

        private void OnRecordAdded(BorrowRecord record)
        {
            if (recordMap.ContainsKey(record.RecordId))
                return;

            var item = Instantiate(itemPrefab, contentRoot);
            item.Init(record.User, record.BorrowCount, record.BorrowTime);

            recordMap.Add(record.RecordId, item);
        }

        private void OnRecordUpdated(BorrowRecord record)
        {
            if (recordMap.TryGetValue(record.RecordId, out var item))
            {
                item.SetReturned(record.ReturnCount, record.ReturnTime);
            }
        }
    }
}

using System;

public static class BeijingTime
{
    /// <summary>
    /// 当前北京时间（UTC + 8）
    /// </summary>
    public static DateTime Now
    {
        get
        {
            return DateTime.UtcNow.AddHours(8);
        }
    }
}

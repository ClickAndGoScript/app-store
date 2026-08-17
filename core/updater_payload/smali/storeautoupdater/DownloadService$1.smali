.class Lstoreautoupdater/DownloadService$1;
.super Ljava/lang/Object;
.source "DownloadService.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lstoreautoupdater/DownloadService;->onStartCommand(Landroid/content/Intent;II)I
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic this$0:Lstoreautoupdater/DownloadService;

.field final synthetic val$downloadUrl:Ljava/lang/String;

.field final synthetic val$version:Ljava/lang/String;


# direct methods
.method constructor <init>(Lstoreautoupdater/DownloadService;Ljava/lang/String;Ljava/lang/String;)V
    .registers 4

    iput-object p1, p0, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    iput-object p2, p0, Lstoreautoupdater/DownloadService$1;->val$downloadUrl:Ljava/lang/String;
    iput-object p3, p0, Lstoreautoupdater/DownloadService$1;->val$version:Ljava/lang/String;
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method


# virtual methods
.method public run()V
    .registers 17

    move-object/from16 v1, p0
    const/4 v0, 0x1
    const v2, 0x1080081
    const-string v3, "notification"

    iget-object v4, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    invoke-virtual {v4, v3}, Landroid/app/Service;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;
    move-result-object v3
    check-cast v3, Landroid/app/NotificationManager;

    new-instance v4, Landroid/app/Notification$Builder;
    iget-object v5, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    const-string v6, "download_channel"
    invoke-direct {v4, v5, v6}, Landroid/app/Notification$Builder;-><init>(Landroid/content/Context;Ljava/lang/String;)V

    invoke-virtual {v4, v2}, Landroid/app/Notification$Builder;->setSmallIcon(I)Landroid/app/Notification$Builder;
    move-result-object v4
    const-string v5, "הורדת עדכון"
    invoke-virtual {v4, v5}, Landroid/app/Notification$Builder;->setContentTitle(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;
    move-result-object v4
    iget-object v5, v1, Lstoreautoupdater/DownloadService$1;->val$version:Ljava/lang/String;
    invoke-virtual {v4, v5}, Landroid/app/Notification$Builder;->setContentText(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;
    move-result-object v4

    const/4 v5, 0x1
    invoke-virtual {v4, v5}, Landroid/app/Notification$Builder;->setAutoCancel(Z)Landroid/app/Notification$Builder;
    move-result-object v4
    
    # השתקת הצפצופים החוזרים של מד ההתקדמות (true)
    invoke-virtual {v4, v5}, Landroid/app/Notification$Builder;->setOnlyAlertOnce(Z)Landroid/app/Notification$Builder;

    const/16 v6, 0x64
    const/4 v7, 0x0
    invoke-virtual {v4, v6, v7, v5}, Landroid/app/Notification$Builder;->setProgress(IIZ)Landroid/app/Notification$Builder;

    invoke-virtual {v4}, Landroid/app/Notification$Builder;->build()Landroid/app/Notification;
    move-result-object v5
    invoke-virtual {v3, v0, v5}, Landroid/app/NotificationManager;->notify(ILandroid/app/Notification;)V

    :try_start_download
    # 1. משיכת התיקייה
    iget-object v5, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    const-string v6, "updates"
    invoke-virtual {v5, v6}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v7

    # 2. בניית שם הקובץ: update-{version}.apk
    new-instance v8, Ljava/lang/StringBuilder;
    invoke-direct {v8}, Ljava/lang/StringBuilder;-><init>()V
    const-string v9, "update-"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    iget-object v9, v1, Lstoreautoupdater/DownloadService$1;->val$version:Ljava/lang/String;
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v9, ".apk"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v8}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v8
    
    new-instance v2, Ljava/io/File;
    invoke-direct {v2, v7, v8}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    # 3. בדיקת קאש: האם הקובץ קיים ומוכן להתקנה?
    invoke-virtual {v2}, Ljava/io/File;->exists()Z
    move-result v9
    if-eqz v9, :cond_clear_dir
    # אם קיים, דלג ישר לסוף! (לא מבזבזים זמן ואינטרנט)
    goto/16 :download_finished

    :cond_clear_dir
    # 4. ניקוי קבצים ישנים (פינוי מקום)
    invoke-virtual {v7}, Ljava/io/File;->listFiles()[Ljava/io/File;
    move-result-object v9
    if-eqz v9, :cond_start_net
    array-length v10, v9
    const/4 v11, 0x0
    :goto_clean_loop
    if-ge v11, v10, :cond_start_net
    aget-object v12, v9, v11
    invoke-virtual {v12}, Ljava/io/File;->delete()Z
    add-int/lit8 v11, v11, 0x1
    goto :goto_clean_loop

    :cond_start_net
    # 5. יצירת אובייקט לקובץ זמני (.tmp) כדי למנוע השחתה באמצע
    new-instance v8, Ljava/lang/StringBuilder;
    invoke-direct {v8}, Ljava/lang/StringBuilder;-><init>()V
    const-string v9, "update-"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    iget-object v9, v1, Lstoreautoupdater/DownloadService$1;->val$version:Ljava/lang/String;
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v9, ".tmp"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v8}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v8
    new-instance v6, Ljava/io/File;
    invoke-direct {v6, v7, v8}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    # 6. פתיחת חיבור רשת להורדה
    const/4 v8, 0x0
    new-instance v5, Ljava/net/URL;
    iget-object v8, v1, Lstoreautoupdater/DownloadService$1;->val$downloadUrl:Ljava/lang/String;
    invoke-direct {v5, v8}, Ljava/net/URL;-><init>(Ljava/lang/String;)V
    invoke-virtual {v5}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;
    move-result-object v5
    invoke-virtual {v5}, Ljava/net/URLConnection;->getInputStream()Ljava/io/InputStream;
    move-result-object v15
    invoke-virtual {v5}, Ljava/net/URLConnection;->getContentLength()I
    move-result v5

    # פתיחת תזרים כתיבה לקובץ הזמני
    new-instance v14, Ljava/io/FileOutputStream;
    invoke-direct {v14, v6}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V
    
    const v7, 0x10000
    new-array v13, v7, [B
    const-wide/16 v10, 0x0
    const/4 v7, -0x1

    :cond_download_loop
    invoke-virtual {v15, v13}, Ljava/io/InputStream;->read([B)I
    move-result v12
    const/4 v8, -0x1
    if-eq v12, v8, :cond_download_end

    const/4 v8, 0x0
    invoke-virtual {v14, v13, v8, v12}, Ljava/io/FileOutputStream;->write([BII)V
    int-to-long v8, v12
    add-long/2addr v10, v8
    if-lez v5, :cond_download_loop

    move-wide v8, v10
    const-wide/16 v1, 0x64
    mul-long/2addr v8, v1
    int-to-long v1, v5
    div-long/2addr v8, v1
    long-to-int v6, v8
    if-eq v6, v7, :cond_download_loop

    move v7, v6
    const/4 v8, 0x0
    const/16 v9, 0x64
    invoke-virtual {v4, v9, v6, v8}, Landroid/app/Notification$Builder;->setProgress(IIZ)Landroid/app/Notification$Builder;
    invoke-virtual {v4}, Landroid/app/Notification$Builder;->build()Landroid/app/Notification;
    move-result-object v6
    invoke-virtual {v3, v0, v6}, Landroid/app/NotificationManager;->notify(ILandroid/app/Notification;)V

    goto :cond_download_loop

    :cond_download_end
    move-object/from16 v1, p0
    invoke-virtual {v14}, Ljava/io/FileOutputStream;->flush()V
    invoke-virtual {v14}, Ljava/io/FileOutputStream;->close()V
    invoke-virtual {v15}, Ljava/io/InputStream;->close()V

    # 7. שחזור האובייקטים (למניעת דריסת זיכרון של ה-Loop)
    iget-object v5, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    const-string v6, "updates"
    invoke-virtual {v5, v6}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v7

    new-instance v8, Ljava/lang/StringBuilder;
    invoke-direct {v8}, Ljava/lang/StringBuilder;-><init>()V
    const-string v9, "update-"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    iget-object v9, v1, Lstoreautoupdater/DownloadService$1;->val$version:Ljava/lang/String;
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v9, ".tmp"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v8}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v8
    new-instance v6, Ljava/io/File;
    invoke-direct {v6, v7, v8}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    new-instance v8, Ljava/lang/StringBuilder;
    invoke-direct {v8}, Ljava/lang/StringBuilder;-><init>()V
    const-string v9, "update-"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    iget-object v9, v1, Lstoreautoupdater/DownloadService$1;->val$version:Ljava/lang/String;
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v9, ".apk"
    invoke-virtual {v8, v9}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v8}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v8
    new-instance v2, Ljava/io/File;
    invoke-direct {v2, v7, v8}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    # שינוי השם מ-tmp ל-apk ברגע שהכל סיים ב-100%
    invoke-virtual {v6, v2}, Ljava/io/File;->renameTo(Ljava/io/File;)Z

    :download_finished
    # כאן אנחנו מתחילים להכין את ההתקנה (עוקף הורדה אם הקובץ נמצא)
    const-string v10, "UpdaterDebug"
    const-string v11, "Download finished. Preparing intent..."
    invoke-static {v10, v11}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    new-instance v5, Landroid/content/Intent;
    const-string v6, "android.intent.action.VIEW"
    invoke-direct {v5, v6}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    # הוספת דגלי מתקין: FLAG_GRANT_READ_URI_PERMISSION + FLAG_ACTIVITY_NEW_TASK
    const v6, 0x10000001
    invoke-virtual {v5, v6}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;

    iget-object v6, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    
    # Provider Placeholder
    const-string v8, "__PROVIDER_AUTHORITY__"

    const-string v10, "UpdaterDebug"
    new-instance v11, Ljava/lang/StringBuilder;
    invoke-direct {v11}, Ljava/lang/StringBuilder;-><init>()V
    const-string v12, "Using Authority: "
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v11, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v11}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v11
    invoke-static {v10, v11}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    const-string v10, "UpdaterDebug"
    new-instance v11, Ljava/lang/StringBuilder;
    invoke-direct {v11}, Ljava/lang/StringBuilder;-><init>()V
    const-string v12, "File path: "
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;
    move-result-object v12
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v11}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v11
    invoke-static {v10, v11}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    invoke-static {v6, v8, v2}, Lstoreautoupdater/GenericFileProvider;->getUriForFile(Landroid/content/Context;Ljava/lang/String;Ljava/io/File;)Landroid/net/Uri;
    move-result-object v6

    const-string v10, "UpdaterDebug"
    new-instance v11, Ljava/lang/StringBuilder;
    invoke-direct {v11}, Ljava/lang/StringBuilder;-><init>()V
    const-string v12, "URI Generated: "
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v6}, Landroid/net/Uri;->toString()Ljava/lang/String;
    move-result-object v12
    invoke-virtual {v11, v12}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v11}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v11
    invoke-static {v10, v11}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    const-string v7, "application/vnd.android.package-archive"
    invoke-virtual {v5, v6, v7}, Landroid/content/Intent;->setDataAndType(Landroid/net/Uri;Ljava/lang/String;)Landroid/content/Intent;

    iget-object v6, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    const/4 v7, 0x0
    
    # תאימות PendingIntent לאנדרואיד 14 (FLAG_IMMUTABLE | FLAG_UPDATE_CURRENT)
    const/high16 v8, 0xc000000

    invoke-static {v6, v7, v5, v8}, Landroid/app/PendingIntent;->getActivity(Landroid/content/Context;ILandroid/content/Intent;I)Landroid/app/PendingIntent;
    move-result-object v5

    const v6, 0x1080082
    invoke-virtual {v4, v6}, Landroid/app/Notification$Builder;->setSmallIcon(I)Landroid/app/Notification$Builder;
    const/4 v6, 0x0
    
    # ביטול השתקת ההתראה (כדי שיצפצף ויסב את תשומת לב המשתמש כשהסתיימה ההורדה)
    invoke-virtual {v4, v6}, Landroid/app/Notification$Builder;->setOnlyAlertOnce(Z)Landroid/app/Notification$Builder;

    invoke-virtual {v4, v6, v6, v6}, Landroid/app/Notification$Builder;->setProgress(IIZ)Landroid/app/Notification$Builder;
    const-string v6, "ההורדה הושלמה"
    invoke-virtual {v4, v6}, Landroid/app/Notification$Builder;->setContentTitle(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;
    const-string v6, "לחץ כאן להתקנת העדכון"
    invoke-virtual {v4, v6}, Landroid/app/Notification$Builder;->setContentText(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;
    invoke-virtual {v4, v5}, Landroid/app/Notification$Builder;->setContentIntent(Landroid/app/PendingIntent;)Landroid/app/Notification$Builder;

    invoke-virtual {v4}, Landroid/app/Notification$Builder;->build()Landroid/app/Notification;
    move-result-object v5
    invoke-virtual {v3, v0, v5}, Landroid/app/NotificationManager;->notify(ILandroid/app/Notification;)V
    :try_end_final
    .catch Ljava/lang/Exception; {:try_start_download .. :try_end_final} :catch_error

    goto :goto_end

    :catch_error
    move-exception v5

    const-string v10, "UpdaterDebug"
    const-string v11, "ERROR in Updater!"
    invoke-static {v10, v11, v5}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    const/4 v6, 0x0
    
    # צפצוף גם במקרה של שגיאה בהורדה
    invoke-virtual {v4, v6}, Landroid/app/Notification$Builder;->setOnlyAlertOnce(Z)Landroid/app/Notification$Builder;

    invoke-virtual {v4, v6, v6, v6}, Landroid/app/Notification$Builder;->setProgress(IIZ)Landroid/app/Notification$Builder;
    const-string v7, "ההורדה נכשלה"
    invoke-virtual {v4, v7}, Landroid/app/Notification$Builder;->setContentTitle(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;
    invoke-virtual {v5}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;
    move-result-object v5
    invoke-virtual {v4, v5}, Landroid/app/Notification$Builder;->setContentText(Ljava/lang/CharSequence;)Landroid/app/Notification$Builder;
    invoke-virtual {v4}, Landroid/app/Notification$Builder;->build()Landroid/app/Notification;
    move-result-object v5
    invoke-virtual {v3, v0, v5}, Landroid/app/NotificationManager;->notify(ILandroid/app/Notification;)V

    :goto_end
    move-object/from16 v1, p0
    iget-object v0, v1, Lstoreautoupdater/DownloadService$1;->this$0:Lstoreautoupdater/DownloadService;
    invoke-virtual {v0}, Landroid/app/Service;->stopSelf()V
    return-void
.end method

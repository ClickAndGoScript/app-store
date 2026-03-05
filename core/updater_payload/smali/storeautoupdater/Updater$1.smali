# classes.dex

.class final Lstoreautoupdater/Updater$1;
.super Ljava/lang/Object;

# interfaces
.implements Ljava/lang/Runnable;

# instance fields
.field final synthetic val$context:Landroid/content/Context;

# direct methods
.method constructor <init>(Landroid/content/Context;)V
    .registers 2
    .param p1, "context"  # Landroid/content/Context;

    iput-object p1, p0, Lstoreautoupdater/Updater$1;->val$context:Landroid/content/Context;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

# virtual methods
.method public run()V
    .registers 12

    :try_start_0
    iget-object v8, p0, Lstoreautoupdater/Updater$1;->val$context:Landroid/content/Context;
    invoke-virtual {v8}, Landroid/content/Context;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v3

    iget-object v8, p0, Lstoreautoupdater/Updater$1;->val$context:Landroid/content/Context;
    invoke-virtual {v8}, Landroid/content/Context;->getPackageName()Ljava/lang/String;
    move-result-object v8

    const/4 v9, 0x0
    invoke-virtual {v3, v8, v9}, Landroid/content/pm/PackageManager;->getPackageInfo(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;
    move-result-object v1

    iget-object v0, v1, Landroid/content/pm/PackageInfo;->versionName:Ljava/lang/String;

    new-instance v7, Ljava/net/URL;
    # --- פלייסחולדר לכתובת קובץ הגרסה ---
    const-string v8, "__VERSION_TXT_URL__"
    invoke-direct {v7, v8}, Ljava/net/URL;-><init>(Ljava/lang/String;)V

    invoke-virtual {v7}, Ljava/net/URL;->openConnection()Ljava/net/URLConnection;
    move-result-object v9
    check-cast v9, Ljava/net/HttpURLConnection;

    const-string v10, "User-Agent"
    const-string v8, "StoreAutoUpdater"
    invoke-virtual {v9, v10, v8}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V

    const-string v10, "Cache-Control"
    const-string v8, "no-cache"
    invoke-virtual {v9, v10, v8}, Ljava/net/HttpURLConnection;->setRequestProperty(Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {v9}, Ljava/net/HttpURLConnection;->getInputStream()Ljava/io/InputStream;
    move-result-object v2

    new-instance v5, Ljava/util/Scanner;
    invoke-direct {v5, v2}, Ljava/util/Scanner;-><init>(Ljava/io/InputStream;)V

    const-string v8, "\\A"
    invoke-virtual {v5, v8}, Ljava/util/Scanner;->useDelimiter(Ljava/lang/String;)Ljava/util/Scanner;
    move-result-object v8

    invoke-virtual {v8}, Ljava/util/Scanner;->next()Ljava/lang/String;
    move-result-object v4

    invoke-virtual {v5}, Ljava/util/Scanner;->close()V

    invoke-virtual {v4}, Ljava/lang/String;->trim()Ljava/lang/String;
    move-result-object v8

    invoke-virtual {v0, v8}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v9

    if-nez v9, :cond_exit

    new-instance v9, Ljava/lang/StringBuilder;
    invoke-direct {v9}, Ljava/lang/StringBuilder;-><init>()V

    # --- פלייסחולדר: קידומת ההורדה (למשל https://github.com/.../download/app-v) ---
    const-string v6, "__RELEASE_DOWNLOAD_PREFIX__"
    invoke-virtual {v9, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v9, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    # --- פלייסחולדר: אמצע ההורדה (למשל /app-patched-) ---
    const-string v6, "__RELEASE_DOWNLOAD_MIDDLE__"
    invoke-virtual {v9, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v9, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v6, ".apk"
    invoke-virtual {v9, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v9}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v9

    new-instance v10, Landroid/os/Handler;
    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;
    move-result-object v1

    invoke-direct {v10, v1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    new-instance v1, Lstoreautoupdater/Updater$1$1;
    invoke-direct {v1, p0, v0, v8, v9}, Lstoreautoupdater/Updater$1$1;-><init>(Lstoreautoupdater/Updater$1;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V

    invoke-virtual {v10, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_exit
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_error

    :goto_exit
    return-void

    :catch_error
    move-exception v8
    const-string v9, "StoreAutoUpdater"
    invoke-virtual {v8}, Ljava/lang/Exception;->toString()Ljava/lang/String;
    move-result-object v10
    invoke-static {v9, v10}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I
    goto :goto_exit
.end method

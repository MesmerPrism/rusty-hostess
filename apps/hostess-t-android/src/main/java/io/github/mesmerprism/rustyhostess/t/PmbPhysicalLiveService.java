package io.github.mesmerprism.rustyhostess.t;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;

public final class PmbPhysicalLiveService extends Service {
    static final String ACTION = "io.github.mesmerprism.rustyhostess.t.RUN_PMB_PHYSICAL_LIVE_BACKGROUND";

    private static final String CHANNEL_ID = "rusty_hostess_pmb_physical_live";
    private static final int NOTIFICATION_ID = 72;
    private Thread workerThread;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null || !ACTION.equals(intent.getAction())) {
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        startForegroundCompat();
        if (workerThread != null && workerThread.isAlive()) {
            return START_NOT_STICKY;
        }
        workerThread = new Thread(() -> {
            try {
                PmbPhysicalLiveRunner.run(getApplicationContext(), intent);
            } finally {
                if (Build.VERSION.SDK_INT >= 24) {
                    stopForeground(STOP_FOREGROUND_REMOVE);
                } else {
                    stopForeground(true);
                }
                stopSelf(startId);
            }
        }, "hostess-pmb-physical-live-service");
        workerThread.start();
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        if (workerThread != null) {
            workerThread.interrupt();
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void startForegroundCompat() {
        createNotificationChannel();
        Notification notification = new Notification.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("Rusty Hostess T")
                .setContentText("Physical PMB route running")
                .setOngoing(true)
                .build();
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT < 26) {
            return;
        }
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Physical PMB route",
                NotificationManager.IMPORTANCE_LOW);
        channel.setShowBadge(false);
        manager.createNotificationChannel(channel);
    }
}

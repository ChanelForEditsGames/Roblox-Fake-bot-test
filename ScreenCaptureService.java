package org.onlyroblox.visualizer;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.IBinder;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Base64;
import android.util.DisplayMetrics;
import android.view.WindowManager;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;

public class ScreenCaptureService extends Service {
    private static final String ACTION_START = "org.onlyroblox.visualizer.START";
    private static final String ACTION_STOP = "org.onlyroblox.visualizer.STOP";
    private static final String CHANNEL_ID = "only_roblox_capture";
    private static final int NOTIFICATION_ID = 7319;

    private static volatile byte[] latestJpeg = null;
    private static volatile long frameCounter = 0;
    private static volatile boolean capturePaused = false;

    private MediaProjection projection;
    private VirtualDisplay virtualDisplay;
    private ImageReader imageReader;
    private HandlerThread imageThread;
    private Handler imageHandler;
    private long lastFrameTime = 0;
    private float cropX = 0f;
    private float cropY = 0f;
    private float cropW = 1f;
    private float cropH = 1f;

    public static void start(Context context, int resultCode, Intent resultData,
                             float x, float y, float width, float height) {
        Intent intent = new Intent(context, ScreenCaptureService.class);
        intent.setAction(ACTION_START);
        intent.putExtra("resultCode", resultCode);
        intent.putExtra("resultData", resultData);
        intent.putExtra("cropX", x);
        intent.putExtra("cropY", y);
        intent.putExtra("cropW", width);
        intent.putExtra("cropH", height);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(intent);
        } else {
            context.startService(intent);
        }
    }

    public static void stop(Context context) {
        Intent intent = new Intent(context, ScreenCaptureService.class);
        intent.setAction(ACTION_STOP);
        context.startService(intent);
    }

    public static String getLatestFrameBase64() {
        byte[] data = latestJpeg;
        if (data == null) return null;
        return Base64.encodeToString(data, Base64.NO_WRAP);
    }

    public static long getFrameCounter() {
        return frameCounter;
    }

    public static void setPaused(boolean paused) {
        capturePaused = paused;
    }

    public static void clearLatestFrame() {
        latestJpeg = null;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopCapture();
            stopForeground(true);
            stopSelf();
            return START_NOT_STICKY;
        }

        Notification notification;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            notification = new Notification.Builder(this, CHANNEL_ID)
                    .setContentTitle("Only Roblox Visualizer")
                    .setContentText("Captura de pantalla activa")
                    .setSmallIcon(android.R.drawable.ic_menu_view)
                    .setOngoing(true)
                    .build();
        } else {
            notification = new Notification.Builder(this)
                    .setContentTitle("Only Roblox Visualizer")
                    .setContentText("Captura de pantalla activa")
                    .setSmallIcon(android.R.drawable.ic_menu_view)
                    .setOngoing(true)
                    .build();
        }
        startForeground(NOTIFICATION_ID, notification);

        if (intent != null && ACTION_START.equals(intent.getAction()) && projection == null) {
            cropX = intent.getFloatExtra("cropX", 0f);
            cropY = intent.getFloatExtra("cropY", 0f);
            cropW = intent.getFloatExtra("cropW", 1f);
            cropH = intent.getFloatExtra("cropH", 1f);
            int resultCode = intent.getIntExtra("resultCode", 0);
            Intent resultData = intent.getParcelableExtra("resultData");
            startCapture(resultCode, resultData);
        }
        return START_NOT_STICKY;
    }

    private void startCapture(int resultCode, Intent resultData) {
        try {
            MediaProjectionManager manager = (MediaProjectionManager)
                    getSystemService(Context.MEDIA_PROJECTION_SERVICE);
            projection = manager.getMediaProjection(resultCode, resultData);
            if (projection == null) {
                stopSelf();
                return;
            }

            DisplayMetrics metrics = new DisplayMetrics();
            WindowManager windowManager = (WindowManager) getSystemService(WINDOW_SERVICE);
            windowManager.getDefaultDisplay().getRealMetrics(metrics);
            int width = metrics.widthPixels;
            int height = metrics.heightPixels;
            int density = metrics.densityDpi;

            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2);
            imageThread = new HandlerThread("OnlyRobloxFrameReader");
            imageThread.start();
            imageHandler = new Handler(imageThread.getLooper());
            imageReader.setOnImageAvailableListener(this::onImageAvailable, imageHandler);

            virtualDisplay = projection.createVirtualDisplay(
                    "OnlyRobloxScreenCapture",
                    width,
                    height,
                    density,
                    DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                    imageReader.getSurface(),
                    null,
                    imageHandler
            );
            projection.registerCallback(new MediaProjection.Callback() {
                @Override
                public void onStop() {
                    stopCapture();
                    stopSelf();
                }
            }, imageHandler);
        } catch (Exception error) {
            stopCapture();
            stopSelf();
        }
    }

    private void onImageAvailable(ImageReader reader) {
        Image image = null;
        try {
            image = reader.acquireLatestImage();
            if (image == null || capturePaused) return;
            long now = SystemClock.elapsedRealtime();
            if (now - lastFrameTime < 350) return;
            lastFrameTime = now;

            Image.Plane plane = image.getPlanes()[0];
            ByteBuffer buffer = plane.getBuffer();
            int pixelStride = plane.getPixelStride();
            int rowStride = plane.getRowStride();
            int width = image.getWidth();
            int height = image.getHeight();
            int paddedWidth = width + (rowStride - pixelStride * width) / pixelStride;

            Bitmap padded = Bitmap.createBitmap(paddedWidth, height, Bitmap.Config.ARGB_8888);
            buffer.rewind();
            padded.copyPixelsFromBuffer(buffer);
            Bitmap screen = Bitmap.createBitmap(padded, 0, 0, width, height);
            padded.recycle();

            int left = Math.max(0, Math.min(width - 1, Math.round(width * cropX)));
            int top = Math.max(0, Math.min(height - 1, Math.round(height * cropY)));
            int cropWidth = Math.max(1, Math.min(width - left, Math.round(width * cropW)));
            int cropHeight = Math.max(1, Math.min(height - top, Math.round(height * cropH)));
            Bitmap cropped = Bitmap.createBitmap(screen, left, top, cropWidth, cropHeight);
            screen.recycle();

            ByteArrayOutputStream output = new ByteArrayOutputStream();
            cropped.compress(Bitmap.CompressFormat.JPEG, 70, output);
            cropped.recycle();
            latestJpeg = output.toByteArray();
            frameCounter++;
            output.close();
        } catch (Exception ignored) {
            // Keep the service alive; a later frame can still be captured.
        } finally {
            if (image != null) image.close();
        }
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Captura de pantalla",
                    NotificationManager.IMPORTANCE_LOW
            );
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) manager.createNotificationChannel(channel);
        }
    }

    private void stopCapture() {
        capturePaused = false;
        latestJpeg = null;
        if (virtualDisplay != null) {
            virtualDisplay.release();
            virtualDisplay = null;
        }
        if (imageReader != null) {
            imageReader.setOnImageAvailableListener(null, null);
            imageReader.close();
            imageReader = null;
        }
        if (projection != null) {
            projection.stop();
            projection = null;
        }
        if (imageThread != null) {
            imageThread.quitSafely();
            imageThread = null;
            imageHandler = null;
        }
    }

    @Override
    public void onDestroy() {
        stopCapture();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}

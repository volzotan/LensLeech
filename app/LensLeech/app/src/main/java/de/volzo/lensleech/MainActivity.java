package de.volzo.lensleech;

import androidx.appcompat.app.ActionBar;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.SurfaceTexture;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.TextureView;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebView;
import android.widget.ImageView;
import android.widget.Toast;

import com.bumptech.glide.Glide;
import com.bumptech.glide.load.engine.DiskCacheStrategy;

import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity implements
        TextureView.SurfaceTextureListener,
        GestureDetector.OnGestureListener,
        SensorController.OnRotationListener {

    private static final String TAG = MainActivity.class.getSimpleName();

    public static final int PERMISSION_REQUEST_CODE = 0x123;

    private CameraControllerX cameraController;
    private SensorController sensorController;
    private DrawSurface drawSurface;

    private List<Uri> capturedImages = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // make the activity fullscreen (removes the top bar with clock and battery info)
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
                WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);

        // remove the action bar (box with activity title/name)
        ActionBar actionBar = getSupportActionBar();
        if (actionBar != null) actionBar.hide();

        View decorView = getWindow().getDecorView();
        int uiOptions = View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_FULLSCREEN;
        decorView.setSystemUiVisibility(uiOptions);

        // use maximum screen brightness
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        WindowManager.LayoutParams params = getWindow().getAttributes();
        params.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_FULL;
        getWindow().setAttributes(params);

        setContentView(R.layout.activity_main);

        // tell the TextureView we want to know if the GPU has initialized it
        // TextureView tv = (TextureView) findViewById(R.id.textureView);
        // tv.setSurfaceTextureListener(this);

        drawSurface = (DrawSurface) findViewById(R.id.drawSurface);

        // initialize our sensors
        if (sensorController == null) {
            sensorController = new SensorController(this);
            sensorController.registerOnRotationListener(this);
        }

        // register the listener
        IntentFilter filter = new IntentFilter();
        //filter.addAction(UdpService.intentName);;
        filter.addAction(CameraControllerX.intentName);
        LocalBroadcastManager.getInstance(this).registerReceiver(this.receiver, filter);

        // ask for permissions
        if (!checkPermissionsAreGiven()) {
            ActivityCompat.requestPermissions(this,
                    new String[]{
                            Manifest.permission.CAMERA,
                            Manifest.permission.RECORD_AUDIO,
                            Manifest.permission.WRITE_EXTERNAL_STORAGE
                    },
                    PERMISSION_REQUEST_CODE);
        } else {
            Log.d(TAG, "permissions are already granted");
            init();
        }

        // do not do anything else in onCreate(). init() will be called once the permissions are granted.
    }

    public boolean checkPermissionsAreGiven() {
        return (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String permissions[], int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        switch (requestCode) {
            case PERMISSION_REQUEST_CODE: {
                boolean success = true;

                for (int i=0; i<grantResults.length; i++) {

                    // even though only still image permissions are required, video/audio is part of the
                    // permission package. But since android never displays the audio request, it is denied.

                    if (permissions[i].equals(Manifest.permission.RECORD_AUDIO)) {
                        continue;
                    }

                    if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                        success = false;
                        break;
                    }
                }

                if (success) {
                    Log.w(TAG, "permissions are granted by user");
                    init();
                } else {
                    Log.w(TAG, "permissions denied by user");
                }
            }
        }
    }

    // permissions are granted, setup everything
    private void init() {

        PreviewView pv = findViewById(R.id.previewView);
        this.cameraController = new CameraControllerX(this, pv, CameraSelector.LENS_FACING_FRONT);

        startService(new Intent(this, UdpService.class));

//        WebView webView = findViewById(R.id.webview);
//        webView.getSettings().setJavaScriptEnabled(true);
//        webView.clearCache(true);
//        webView.loadUrl("192.168.178.20:8000");

        try {
            //LeechDetector leech = new LeechDetector();
            //Streamer streamer = new Streamer(this, null);
        } catch (Exception e) {
            e.printStackTrace();
        }

//        @SuppressLint("UnsafeExperimentalUsageError")
//        ViewPort vp = pv.getViewPort();
//        vp.getAspectRatio();
//        vp.getLayoutDirection();
//        vp.getRotation();
//        vp.getScaleType();

        // the textureView may not be instantly available
        // if we can use it we use it, otherwise we will call
        // this method again from the available-callback

//        TextureView tv = (TextureView) findViewById(R.id.textureView);
//        if (tv.isAvailable()) {
//
//            cameraController = new CameraControllerX(this, tv);
//
//            try {
//                Log.d(TAG, "opening camera...");
//                cameraController.openCamera();
//            } catch (Exception e) {
//                Log.e(TAG, "open camera failed", e);
//            }
//        } else {
//            Log.w(TAG, "textureView not (yet) available");
//        }
    }

    LeechStatus lastLeechStatus;
    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {

            if (intent.getAction().equals(CameraControllerX.intentName)) {
                Log.wtf(TAG, intent.toString());

                try {

                    capturedImages.add(Uri.parse(intent.getStringExtra("uri")));

                    ImageView[] iv = {(ImageView) findViewById(R.id.imageView0), (ImageView) findViewById(R.id.imageView1), (ImageView) findViewById(R.id.imageView2)};

                    for (int i=0; i<Math.min(3, capturedImages.size()); i++) {
                        Glide.with(context)
                                .load(capturedImages.get(capturedImages.size()-1-i))
                                .diskCacheStrategy(DiskCacheStrategy.NONE)
                                .skipMemoryCache(true)
                                .into(iv[i]);
                        Log.d(TAG, "loading image " + Integer.toString(capturedImages.size()-1-i) + " into " + i);
                    }

                } catch (Exception e) {
                    Log.e(TAG, "displaying captured image failed: " + e.toString());
                }

            } else if (intent.getAction().equals(UdpService.intentName)) {
                LeechStatus leechStatus = (LeechStatus) intent.getSerializableExtra("status");
                drawSurface.setLeechStatus(leechStatus);

                if (
                        lastLeechStatus != null &&
                        lastLeechStatus.press != null &&
                        leechStatus != null &&
                        leechStatus.press != null &&
                        lastLeechStatus.press == false &&
                        leechStatus.press == true
                ) {
                    cameraController.takePicture();
                }

                lastLeechStatus = leechStatus;
            } else {
                Log.e(TAG, "unknown intent: " + intent.getAction());
            }
        }
    };

    @Override
    public void onRotation(float angle) {
        if (drawSurface != null) {
            drawSurface.setAngle(angle);
        }
    }

    @Override
    public void onSurfaceTextureAvailable(SurfaceTexture surfaceTexture, int i, int i1) {

        Log.d(TAG, "textureView is available");

        if (checkPermissionsAreGiven()) {
            init();
        } else {
            Log.e(TAG, "camera inactive : permissions are missing");
            Toast.makeText(this, "camera inactive : permissions are missing", Toast.LENGTH_LONG).show();
        }
    }

    @Override
    public void onSurfaceTextureSizeChanged(SurfaceTexture surface, int width, int height) {}

    @Override
    public boolean onSurfaceTextureDestroyed(SurfaceTexture surface) {
        return false;
    }

    @Override
    public void onSurfaceTextureUpdated(SurfaceTexture surface) {}

    @Override
    public boolean onDown(MotionEvent e) {
        // cameraController.takePicture();
        return true;
    }

    @Override
    public void onShowPress(MotionEvent e) {}

    @Override
    public boolean onSingleTapUp(MotionEvent e) {
        return false;
    }

    @Override
    public boolean onScroll(MotionEvent e1, MotionEvent e2, float distanceX, float distanceY) {
        Log.d(TAG, "scroll");
        return false;
    }

    @Override
    public void onLongPress(MotionEvent e) {
        Log.d(TAG, "longPress");
        cameraController.toggleRecording();
        // cameraController.takePicture();
    }

    @Override
    public boolean onFling(MotionEvent e1, MotionEvent e2, float velocityX, float velocityY) {
        Log.d(TAG, "fling");
        return true;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopService(new Intent(this, UdpService.class));
        LocalBroadcastManager.getInstance(this).unregisterReceiver(this.receiver);
    }
}
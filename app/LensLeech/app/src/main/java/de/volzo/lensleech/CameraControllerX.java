package de.volzo.lensleech;


import android.annotation.SuppressLint;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.hardware.camera2.CameraCharacteristics;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.Log;
import android.util.Size;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.camera.camera2.interop.Camera2CameraInfo;
import androidx.camera.camera2.interop.ExperimentalCamera2Interop;
import androidx.camera.core.Camera;
import androidx.camera.core.CameraControl;
import androidx.camera.core.CameraInfo;
import androidx.camera.core.CameraProvider;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.video.FileOutputOptions;
import androidx.camera.video.MediaStoreOutputOptions;
import androidx.camera.video.Recording;
import androidx.camera.video.RecordingStats;
import androidx.camera.video.VideoCapture;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.video.Recorder;
import androidx.camera.video.VideoRecordEvent;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.LifecycleOwner;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import com.google.common.util.concurrent.ListenableFuture;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;

public class CameraControllerX {

    private String TAG = CameraControllerX.class.getSimpleName();
    public static final String intentName = "ImageTakenIntent";
    private Context context;

    private PreviewView previewView;
    private ListenableFuture<ProcessCameraProvider> cameraProviderFuture;

    //static final Size ANALYZE_RESOLUTION = new Size(1280, 720);
    static final Size ANALYZE_RESOLUTION = new Size(640, 480);
    private int cameraType = CameraSelector.LENS_FACING_FRONT;

    private CameraInfo cameraInfo;
    private CameraControl cameraControl;

    private ProcessCameraProvider cameraProvider;

    // Executor executor = ContextCompat.getMainExecutor(context);
    Executor executor = Executors.newSingleThreadExecutor();

    private Recorder recorder;
    private Recording recording;

    // usecases
    Preview preview = null;
    ImageAnalysis imageAnalysis;
    ImageCapture imageCapture;
    VideoCapture videoCapture;

    private Streamer streamer;
    private LeechDetector detector;

    private int imagecounter = 0;

    public CameraControllerX(Context context, PreviewView previewView, Integer cameraType) {
        this.context = context;
        this.previewView = previewView;

        if (cameraType != null){
            this.cameraType = (int) cameraType;
        }

        this.cameraProviderFuture = ProcessCameraProvider.getInstance(context);

        Log.i(TAG, "starting CameraControllerX");

//        try {
//            streamer = new Streamer(context, ANALYZE_RESOLUTION);
//        } catch (Exception e) {
//            Log.e(TAG, e.toString());
//            e.printStackTrace();
//        }

        detector = new LeechDetector(ANALYZE_RESOLUTION);

        cameraProviderFuture.addListener(new Runnable() {
            @Override
            public void run() {
                try {
                    ProcessCameraProvider provider = cameraProviderFuture.get();

                    if (!isCameraLevel3Device(provider, CameraSelector.DEFAULT_FRONT_CAMERA)) {
                        Log.e(TAG, "(front) camera is not a level 3 device!");
                    }

                    if (!isCameraLevel3Device(provider, CameraSelector.DEFAULT_BACK_CAMERA)) {
                        Log.e(TAG, "(back) camera is not a level 3 device!");
                    }

                    cameraProvider = provider;
                    createUsecases();
                    bindPreview();
                } catch (ExecutionException | InterruptedException e) {
                    // No errors need to be handled for this Future.
                    // This should never be reached.
                }
            }
        }, ContextCompat.getMainExecutor(context));
    }

    void createUsecases() {

        // executor = ContextCompat.getMainExecutor(context);
        executor = Executors.newSingleThreadExecutor();

        // Preview
        if (this.previewView != null) {
            // do not scale the image to fit the previewView fully (may crop)
            // but fit it to the longer side (adding black bars) and align it with right end of the view
            previewView.setScaleType(PreviewView.ScaleType.FIT_END);

            Preview.Builder previewBuilder = new Preview.Builder();
            previewBuilder.setTargetResolution(new Size(720, 720));
            preview = previewBuilder.build();
            preview.setSurfaceProvider(previewView.getSurfaceProvider());
        }

        // Recording
        Recorder.Builder recorderBuilder = new Recorder.Builder();
        // recorderBuilder.setQualitySelector();
        this.recorder = recorderBuilder.build();
        videoCapture = VideoCapture.withOutput(this.recorder);

        // Image capture
        imageCapture = new ImageCapture.Builder().build();

        // Analysis
        ImageAnalysis.Builder analysisBuilder = new ImageAnalysis.Builder();
        analysisBuilder.setTargetResolution(ANALYZE_RESOLUTION);
        analysisBuilder.setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST);
        imageAnalysis = analysisBuilder.build();
        imageAnalysis.setAnalyzer(executor, new ImageAnalysis.Analyzer() {
            @Override
            public void analyze(@NonNull ImageProxy imageProxy) {

                //streamer.send(image);
                //streamer.send(imageProxy);

                try {
                    detector.run(imageProxy);
                } catch (Exception e) {
                    Log.e(TAG, "detector failed: " + e.toString());
                    e.printStackTrace();
                }

                imageProxy.close();
            }
        });
    }

    void bindPreview() {

        // Camera Selector
        CameraSelector cameraSelector = new CameraSelector.Builder()
                .requireLensFacing(this.cameraType)
                .build();

        if (this.previewView != null){
            Camera camera = cameraProvider.bindToLifecycle((LifecycleOwner) this.context,
                    cameraSelector,
                    imageAnalysis,
                    preview);
                    //videoCapture);

            this.cameraControl = camera.getCameraControl();
        } else {
            Camera camera = cameraProvider.bindToLifecycle((LifecycleOwner) this.context,
                    cameraSelector,
                    imageAnalysis);
        }
    }

    @androidx.annotation.OptIn(markerClass = ExperimentalCamera2Interop.class)
    Boolean isCameraLevel3Device(ProcessCameraProvider cameraProvider, CameraSelector cam) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            List filteredCameraInfos = cam.filter(cameraProvider.getAvailableCameraInfos());
            if (!filteredCameraInfos.isEmpty()) {
                return Objects.equals(
                        Camera2CameraInfo.from((CameraInfo) filteredCameraInfos.get(0)).getCameraCharacteristic(
                                CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL),
                        CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_3);
            }
        }
        return false;
    }

    public void takePicture() {

        cameraProvider.unbindAll();

        CameraSelector cameraSelector = new CameraSelector.Builder()
                .requireLensFacing(CameraSelector.LENS_FACING_BACK)
                .build();

        Camera camera = cameraProvider.bindToLifecycle((LifecycleOwner) this.context,
                cameraSelector,
                imageCapture,
                preview);

        ImageCapture.OutputFileOptions outputFileOptions = new ImageCapture.OutputFileOptions.Builder(new File(context.getFilesDir() + "/temp_" + imagecounter + ".jpg")).build();
        imagecounter += 1;

        // AWB algorithm takes a bit of warmup time after opening the rear camera
        try {
            Thread.sleep(500);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }

        imageCapture.takePicture(outputFileOptions, executor,
                        new ImageCapture.OnImageSavedCallback() {
                            @Override
                            public void onImageSaved(ImageCapture.OutputFileResults outputFileResults) {
                                Log.i(TAG, "image saved to " + outputFileResults.getSavedUri());

                                Intent intent = new Intent(intentName);
                                intent.putExtra("uri", outputFileResults.getSavedUri().toString());
                                LocalBroadcastManager.getInstance(context).sendBroadcast(intent);

                                new Handler(Looper.getMainLooper()).post(new Runnable() {
                                    @Override
                                    public void run() {
                                        cameraProvider.unbindAll();
                                        bindPreview();
                                    }
                                });
                            }
                            @Override
                            public void onError(ImageCaptureException error) {
                                Log.e(TAG, "image saving failed: " + error.getMessage());

                                new Handler(Looper.getMainLooper()).post(new Runnable() {
                                    @Override
                                    public void run() {
                                        cameraProvider.unbindAll();
                                        bindPreview();
                                    }
                                });
                            }
                        }
                );
    }

    @SuppressLint("MissingPermission")
    public void toggleRecording() {

        if (this.recording == null){
            Log.i(TAG, "start recording");
            Toast.makeText(context, "start recording", Toast.LENGTH_LONG).show();

            String filename = "lensleech-" +
                    new SimpleDateFormat("yyyy-MM-dd-HH-mm-ss-SSS", Locale.US).format(System.currentTimeMillis()) + ".mp4";
            File file = new File(filename);
            FileOutputOptions fileOutputOptions = new FileOutputOptions.Builder(file)
                    .setFileSizeLimit(1024 * 1024).build();

            ContentValues contentValues = new ContentValues();
            contentValues.put(MediaStore.MediaColumns.DISPLAY_NAME, filename);
            contentValues.put(MediaStore.MediaColumns.MIME_TYPE, "video/mp4");
            if (Build.VERSION.SDK_INT > Build.VERSION_CODES.P) {
                contentValues.put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/LensLeech");
            }

            MediaStoreOutputOptions mediaStoreOutputOptions = new MediaStoreOutputOptions
                .Builder(context.getApplicationContext().getContentResolver(), MediaStore.Video.Media.EXTERNAL_CONTENT_URI)
                .setContentValues(contentValues)
                .build();

            this.recording = this.recorder
                    //.prepareRecording(context, fileOutputOptions)
                    .prepareRecording(context, mediaStoreOutputOptions)
                    .withAudioEnabled()
                    .start(ContextCompat.getMainExecutor(this.context), videoRecordEvent -> {
                        if (videoRecordEvent instanceof VideoRecordEvent.Start) {
                            // Handle the start of a new active recording
                            Log.i(TAG, "video record start");
                        } else if (videoRecordEvent instanceof VideoRecordEvent.Pause) {
                            // Handle the case where the active recording is paused
                            Log.i(TAG, "video record pause");
                        } else if (videoRecordEvent instanceof VideoRecordEvent.Resume) {
                            // Handles the case where the active recording is resumed
                            Log.i(TAG, "video record resume");
                        } else if (videoRecordEvent instanceof VideoRecordEvent.Finalize) {
                            VideoRecordEvent.Finalize finalizeEvent = (VideoRecordEvent.Finalize) videoRecordEvent;
                            // Handles a finalize event for the active recording, checking Finalize.getError()
                            Log.i(TAG, "video record finalize");
                            int error = finalizeEvent.getError();
                            if (error != VideoRecordEvent.Finalize.ERROR_NONE) {
                                Log.e(TAG, "video record finalize error: " + error);
                            }
                        }

                        // All events, including VideoRecordEvent.Status, contain RecordingStats.
                        // This can be used to update the UI or track the recording duration.
                        RecordingStats recordingStats = videoRecordEvent.getRecordingStats();
                    });
        } else {
            Log.i(TAG, "stopping recording");
            Toast.makeText(context, "stopping recording", Toast.LENGTH_LONG).show();
            this.recording.stop();
            this.recording = null;
        }
    }

}

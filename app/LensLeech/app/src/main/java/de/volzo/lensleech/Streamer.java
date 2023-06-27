package de.volzo.lensleech;

import android.annotation.SuppressLint;

import android.content.Context;
import android.graphics.Bitmap;
import android.util.Log;
import android.util.Size;

import androidx.camera.core.ImageProxy;

import com.arthenica.ffmpegkit.FFmpegKit;
import com.arthenica.ffmpegkit.FFmpegKitConfig;
import com.arthenica.ffmpegkit.FFmpegSession;
import com.arthenica.ffmpegkit.FFmpegSessionCompleteCallback;
import com.arthenica.ffmpegkit.LogCallback;
import com.arthenica.ffmpegkit.ReturnCode;
import com.arthenica.ffmpegkit.SessionState;
import com.arthenica.ffmpegkit.Statistics;
import com.arthenica.ffmpegkit.StatisticsCallback;
import com.google.mlkit.vision.common.InputImage;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;

public class Streamer {

    private final String TAG = Streamer.class.getSimpleName();

    OutputStream out;

    @SuppressLint("DefaultLocale")
    public Streamer(Context context, Size resolution) throws IOException, InterruptedException {

        final String rtp_url = "rtp://192.168.178.20:9000";
        final String sdpFile = context.getFilesDir() + "/stream.sdp";
        final String pipe1 = FFmpegKitConfig.registerNewFFmpegPipe(context);

        Log.d(TAG, "FFmpeg camera IDs: " + FFmpegKitConfig.getSupportedCameraIds(context));

        //FFmpegKit.executeAsync("-f rawvideo -pixel_format nv21 -video_size " + resolution.getWidth() + "x" + resolution.getHeight() + " -i " + pipe1 + " -f rtp_mpegts" + " " + rtp_url, new FFmpegSessionCompleteCallback() {
        //FFmpegKit.executeAsync("-f rawvideo -pixel_format yuv420p -video_size " + resolution.getWidth() + "x" + resolution.getHeight() + " -i " + pipe1 + " -f rtp_mpegts" + " " + rtp_url, new FFmpegSessionCompleteCallback() {
        //FFmpegKit.executeAsync("-f rawvideo -pixel_format yuv420p -video_size " + resolution.getWidth() + "x" + resolution.getHeight() + " -i " + pipe1 + " -f rtp -sdp_file " + sdpFile + " " + rtp_url, new FFmpegSessionCompleteCallback() {
        //FFmpegKit.executeAsync("-f android_camera -video_size 1280x720 -framerate 5 -camera_index 1 -i 0 -pixel_format bgr0 -q:v 5 -f rtp_mpegts" + " " + rtp_url, new FFmpegSessionCompleteCallback() {
        //FFmpegKit.executeAsync("-codecs", new FFmpegSessionCompleteCallback() {
        FFmpegKit.executeAsync("-f android_camera -input_queue_size 5 -framerate 20 -video_size 1280x720 -camera_index 1 -i 0 -pixel_format yuv420p -q:v 5 -tune zerolatency -preset ultrafast -f rtp -sdp_file " + sdpFile + " " + rtp_url, new FFmpegSessionCompleteCallback() {
        //FFmpegKit.executeAsync("-f android_camera -video_size 1280x720 -framerate 5 -camera_index 1 -i 0 -pixel_format yuv420p -vcodec libvpx -f rtp -sdp_file " + sdpFile + " " + rtp_url, new FFmpegSessionCompleteCallback() {
                @Override
            public void apply(FFmpegSession session) {
                SessionState state = session.getState();
                ReturnCode returnCode = session.getReturnCode();

                FFmpegKitConfig.closeFFmpegPipe(pipe1);

                Log.d(TAG, String.format("FFmpeg process exited with state %s and rc %s.%s", state, returnCode, session.getFailStackTrace()));
            }
        }, new LogCallback() {
            @Override
            public void apply(com.arthenica.ffmpegkit.Log log) {
                Log.d(TAG, "FFMPEG: " + log.getMessage());
            }
        }, new StatisticsCallback() {
            @Override
            public void apply(Statistics statistics) {
            }
        });

        out = new FileOutputStream(pipe1);

        // OutputStreamWriter out;
//
//        byte img[] = new byte[rows*cols*3];   //Dummy image
//
//        try {
//                for (int i=0; i<100000; i++) {
//                    out.write(img);
//                    //out.flush();
//                }
//        } catch (Exception e) {
//            Log.e(TAG, "Error: during writing");
//            e.printStackTrace();
//        } finally {
//            out.close();
//            Log.i(TAG, "Attempt ended");
//        }

    }

    public void send(ImageProxy imageProxy) {

        try {


//                ByteBuffer yBuffer = imageProxy.getPlanes()[0].getBuffer();
//                ByteBuffer uBuffer = imageProxy.getPlanes()[1].getBuffer();
//                ByteBuffer vBuffer = imageProxy.getPlanes()[2].getBuffer();
//
//                int ySize = yBuffer.remaining();
//                int uSize = uBuffer.remaining();
//                int vSize = vBuffer.remaining();
//
//                byte[] nv21 = new byte[ySize + uSize + vSize];
//
//                //U and V are swapped
//                yBuffer.get(nv21, 0, ySize);
//                vBuffer.get(nv21, ySize, vSize);
//                uBuffer.get(nv21, ySize + vSize, uSize);
//
//            out.write(nv21);

//            ImageProxy.PlaneProxy Y = imageProxy.getPlanes()[0];
//            ImageProxy.PlaneProxy U = imageProxy.getPlanes()[1];
//            ImageProxy.PlaneProxy V = imageProxy.getPlanes()[2];
//
//            int Yb = Y.getBuffer().remaining();
//            int Ub = U.getBuffer().remaining();
//            int Vb = V.getBuffer().remaining();
//
//            byte[] data = new byte[Yb + Ub + Vb];
//
//            Y.getBuffer().get(data, 0, Yb);
//            V.getBuffer().get(data, Yb, Ub);
//            U.getBuffer().get(data, Yb+ Ub, Vb);

//            out.write(nv21);

//            WritableByteChannel channel = Channels.newChannel(out);
//
//            channel.write(imageProxy.getPlanes()[0].getBuffer());
//            channel.write(imageProxy.getPlanes()[1].getBuffer());
//            channel.write(imageProxy.getPlanes()[2].getBuffer());



        } catch (Exception e) {
            Log.e(TAG, "sending failed: " + e.toString());
        }
    }

    public void send(InputImage image) {
        try {
            Bitmap bmp = image.getBitmapInternal();
            image.getByteBuffer();
            bmp.compress(Bitmap.CompressFormat.JPEG, 50, out);
        } catch (Exception e) {
            Log.e(TAG, "compressing failed: " + e.toString());
        }
    }
}

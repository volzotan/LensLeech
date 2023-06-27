package de.volzo.lensleech;

import static org.opencv.core.Core.inRange;
import static org.opencv.core.CvType.CV_8UC1;
import static org.opencv.core.CvType.CV_8UC3;
import static org.opencv.imgproc.Imgproc.dilate;
import static org.opencv.imgproc.Imgproc.erode;

import android.os.Bundle;
import android.util.Log;
import android.util.Size;

import androidx.camera.core.ImageProxy;

import org.json.JSONArray;
import org.json.JSONObject;
import org.opencv.android.OpenCVLoader;
import org.opencv.core.KeyPoint;
import org.opencv.core.Mat;
import org.opencv.core.MatOfKeyPoint;
import org.opencv.core.Point;
import org.opencv.core.Scalar;
import org.opencv.features2d.SimpleBlobDetector;
import org.opencv.features2d.SimpleBlobDetector_Params;
import org.opencv.imgproc.Imgproc;

import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketAddress;
import java.net.SocketException;
import java.net.UnknownHostException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.util.List;

public class LeechDetector {

    private final String TAG = LeechDetector.class.getSimpleName();

    private final SocketAddress UDP_ADDRESS = new InetSocketAddress("192.168.178.20", 5004);
    // private final SocketAddress UDP_ADDRESS = new InetSocketAddress("192.168.178.255", 5004);

    Mat mYuv;
    Mat hsv;
    byte[] nv21;

    Mat kernel3;
    Mat kernel7;

    SimpleBlobDetector detector_round;
    DatagramSocket socket;

    // green channel
    private final Scalar low_1 = new Scalar(30, 30, 40);
    private final Scalar high_1 = new Scalar(94-20, 255, 255);

    // blue channel
    private final Scalar low_0 = new Scalar(95-20, 30, 40);
    private final Scalar high_0 = new Scalar(140, 255, 255);

    // red channel
    private final Scalar low_ring1 = new Scalar(140+30, 120, 120);
    private final Scalar high_ring1 = new Scalar(180, 255, 255);
    private final Scalar low_ring2 = new Scalar(0, low_ring1.val[1], low_ring1.val[2]);
    private final Scalar high_ring2 = new Scalar(30-20, 255, 255);

    public LeechDetector(Size size) {

        if (!OpenCVLoader.initDebug())
            Log.e("OpenCV", "Unable to load OpenCV!");
        else
            Log.d("OpenCV", "OpenCV loaded Successfully!");

        mYuv = new Mat(size.getHeight() + size.getHeight() / 2, size.getWidth(), CV_8UC1);
        hsv = new Mat(size.getHeight(), size.getWidth(), CV_8UC3);
        nv21 = new byte[size.getHeight() * size.getWidth() * 2];

        kernel3 = Imgproc.getStructuringElement(Imgproc.MORPH_RECT, new org.opencv.core.Size(3, 3));
        kernel7 = Imgproc.getStructuringElement(Imgproc.MORPH_RECT, new org.opencv.core.Size(7, 7));

        SimpleBlobDetector_Params params = new SimpleBlobDetector_Params();

        params.set_minDistBetweenBlobs(15);

        params.set_filterByColor(false);

        params.set_filterByArea(true);
        params.set_minArea(100);
        params.set_maxArea(6000);

        params.set_filterByInertia(false);
        params.set_filterByConvexity(false);

        detector_round = SimpleBlobDetector.create(params);

        try {
            socket = new DatagramSocket();
        } catch (SocketException e) {
            Log.e(TAG, "creating UDP socket failed: " + e.toString());
        }
    }

    private void send(JSONObject payload) throws IOException {

//
//        new Thread(new Runnable(){
//            @Override
//            public void run() {

                byte[] message = payload.toString().getBytes(StandardCharsets.UTF_8);
                DatagramPacket p = new DatagramPacket(message, message.length, UDP_ADDRESS);
                try {
                    socket.send(p);
                } catch (IOException e) {
                    e.printStackTrace();
                }
//            }
//        }).start();

    }

    public void run(ImageProxy image) throws Exception {
        convert(image);

        Mat image_0 = new Mat(hsv.size(), CV_8UC1);
        Mat image_1 = new Mat(hsv.size(), CV_8UC1);

        Mat filtered_0 = new Mat(hsv.size(), CV_8UC1);
        Mat filtered_1 = new Mat(hsv.size(), CV_8UC1);

        inRange(hsv, low_0, high_0, image_0);
        inRange(hsv, low_1, high_1, image_1);

        erode(image_0, filtered_0, kernel3, new Point(-1, -1), 2);
        erode(image_1, filtered_1, kernel3, new Point(-1, -1), 2);

        dilate(filtered_0, filtered_0, kernel7);
        dilate(filtered_1, filtered_1, kernel7);

        MatOfKeyPoint blobs_0 = new MatOfKeyPoint();
        MatOfKeyPoint blobs_1 = new MatOfKeyPoint();

        detector_round.detect(filtered_0, blobs_0);
        detector_round.detect(filtered_1, blobs_1);

        int[][] data = new int[(int) (blobs_0.size().height + blobs_1.size().height)][4];

        // TODO: unnecessary copy action happening here
        List<KeyPoint> blobs_0_list = blobs_0.toList();
        List<KeyPoint> blobs_1_list = blobs_1.toList();

        for (int i=0; i<blobs_0_list.size(); i++) {
            data[i][0] = (int) (blobs_0_list.get(i).pt.x - hsv.size().width/2);
            data[i][1] = (int) (blobs_0_list.get(i).pt.y - hsv.size().height/2);
            data[i][2] = (int) blobs_0_list.get(i).size;
            data[i][3] = 0;
        }

        for (int i=0; i<blobs_1_list.size(); i++) {
            data[blobs_0_list.size() + i][0] = (int) (blobs_1_list.get(i).pt.x - hsv.size().width/2);
            data[blobs_0_list.size() + i][1] = (int) (blobs_1_list.get(i).pt.y - hsv.size().height/2);
            data[blobs_0_list.size() + i][2] = (int) blobs_1_list.get(i).size;
            data[blobs_0_list.size() + i][3] = 1;
        }

        JSONArray data2 = new JSONArray(data);

        JSONObject payload = new JSONObject();
        payload.put("data", data2);

        send(payload);

        //Imgproc.adaptiveThreshold(mGray, mGray, 255, Imgproc.ADAPTIVE_THRESH_MEAN_C, Imgproc.THRESH_BINARY, 79, 2); //127, 2);

        //Imgproc.morphologyEx(mGray, mGray, Imgproc.MORPH_OPEN, kernel);
        //Imgproc.morphologyEx(mGray, mGray, Imgproc.MORPH_CLOSE, kernel);

    }

    private void convert(ImageProxy imageProxy) {

        ByteBuffer yBuffer = imageProxy.getPlanes()[0].getBuffer();
        ByteBuffer uBuffer = imageProxy.getPlanes()[1].getBuffer();
        ByteBuffer vBuffer = imageProxy.getPlanes()[2].getBuffer();

        int ySize = yBuffer.remaining();
        int uSize = uBuffer.remaining();
        int vSize = vBuffer.remaining();

        //U and V are swapped
        yBuffer.get(nv21, 0, ySize);
        vBuffer.get(nv21, ySize, vSize);
        uBuffer.get(nv21, ySize + vSize, uSize);

        mYuv.put(0, 0, nv21);
        Imgproc.cvtColor(mYuv, hsv, Imgproc.COLOR_YUV2BGR_NV21, 3);
        Imgproc.cvtColor(hsv, hsv, Imgproc.COLOR_BGR2HSV, 3);
    }

}

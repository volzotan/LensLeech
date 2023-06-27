package de.volzo.lensleech;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

public class UdpService extends Service {

    private static final String TAG = UdpService.class.getSimpleName();
    public static final String intentName = "UdpServiceIntent";

    private Context context;
    private Handler handler;

    public static final int UDP_PORT = 5005;

    Thread serverThread;

    @Override
    public IBinder onBind(Intent intent) {
        // TODO: Return the communication channel to the service.
        throw new UnsupportedOperationException("Not yet implemented");
    }

    @Override
    public void onCreate() {
        Log.d(TAG, "onCreate");
    }

    @Override
    public void onDestroy() {
        Log.d(TAG, "onDestroy");

        if (this.serverThread != null && this.serverThread.isAlive()) {
            this.serverThread.stop();
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {

        if (Looper.myLooper() == Looper.getMainLooper()) {
            Log.d(TAG, "UdpService is running on UI thread");
        } else {
            Log.d(TAG, "UdpService is running on thread: " + Thread.currentThread().getName());
        }

        this.context = this;
        this.handler = new Handler(Looper.getMainLooper());

        this.serverThread = new Thread(new ServerThread());
        this.serverThread.start();

        Log.i(TAG, "UdpService started successfully");

        return START_STICKY;
    }

    class ServerThread implements Runnable {

        public void run() {
            try {

                DatagramSocket datagramsocket = new DatagramSocket(UDP_PORT, InetAddress.getByName("0.0.0.0"));
                byte[] buffer = new byte[4096];
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);

                while (true) {

                    datagramsocket.receive(packet);

                    String text = new String(buffer, 0, packet.getLength());
                    // Log.d("UDP packet received", text);

                    Intent intent = new Intent(intentName);
                    intent.putExtra("status", new LeechStatus(text));
                    LocalBroadcastManager.getInstance(context).sendBroadcast(intent);
                }
            } catch (Exception e) {
                Log.e(TAG, e.getMessage());
                System.err.println(e);
                e.printStackTrace();
            }
        }
    }
}

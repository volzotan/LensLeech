package de.volzo.lensleech;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.util.Log;

import java.util.ArrayList;
import java.util.List;

public class SensorController implements SensorEventListener {

    private static final String TAG = MainActivity.class.getSimpleName();

    private Context context;

    private SensorManager sensorManager;

    private Sensor accelerometer;
    private Sensor magnetometer;

    private List<OnRotationListener> onRotationListeners;

    private float[] mGravity;
    private float[] mGeomagnetic;
    private float azimuth;
    private float pitch;
    private float roll;

    public SensorController(Context context) {

        this.context = context;
        sensorManager = (SensorManager) context.getSystemService(Context.SENSOR_SERVICE);

        onRotationListeners = new ArrayList<OnRotationListener>();

        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_FASTEST);

        magnetometer = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);
        sensorManager.registerListener(this, magnetometer, SensorManager.SENSOR_DELAY_FASTEST);
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER)
            mGravity = event.values;

        if (event.sensor.getType() == Sensor.TYPE_MAGNETIC_FIELD)
            mGeomagnetic = event.values;

        if (mGravity != null && mGeomagnetic != null) {
            float R[] = new float[9];
            float I[] = new float[9];

            boolean success = SensorManager.getRotationMatrix(R, I, mGravity, mGeomagnetic);
            if (success) {
                float orientation[] = new float[3];
                SensorManager.getOrientation(R, orientation);

                // orientation contains: azimuth, pitch and roll
                azimuth = orientation[0];
                pitch = orientation[1];
                roll = orientation[2];

                StringBuilder sb = new StringBuilder();
                sb.append(Math.toDegrees(azimuth)); sb.append(" ");
                sb.append(Math.toDegrees(pitch)); sb.append(" ");
                sb.append(Math.toDegrees(roll));;

                // Log.d(TAG, sb.toString());

                for (OnRotationListener l : onRotationListeners) {
                    l.onRotation((float) Math.toDegrees(pitch));
                }
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int i) {

    }

    public void registerOnRotationListener(OnRotationListener listener) {
        onRotationListeners.add(listener);
    }

    public interface OnRotationListener {
        void onRotation(float angle);
    }
}


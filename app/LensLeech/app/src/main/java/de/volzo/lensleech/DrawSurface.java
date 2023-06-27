package de.volzo.lensleech;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.DashPathEffect;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.PorterDuff;
import android.graphics.Rect;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.util.Log;
import android.util.Size;
import android.view.GestureDetector;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class DrawSurface extends SurfaceView implements SurfaceHolder.Callback {

    private static final String TAG = DrawSurface.class.getSimpleName();

    private boolean drawViewfinder = true;
    private boolean drawFramelines = false;
    private boolean drawAngle = false;
    private boolean drawLeech = true;
    private boolean drawIllumination = true;

    private DrawSurfaceCallback onReadyCallback;
    private boolean interactive = false;

    private SurfaceHolder holder = null;
    private final Context context;
    private GestureDetector gestureDetector;

    public Paint paintWhite = null;
    public Paint paintGrey = null;
    public Paint paintTranslucent = null;
    public Paint paintGreen = null;
    public Paint paintRed = null;
    public Paint paintShine = null;
    public Paint paintBackground = null;
    public Paint paintFramelines = null;
    public Paint paintText = null;
    public Paint paintTextCentered = null;

    public Paint paintSolidGreen = null;
    public Paint paintSolidWhite = null;
    public Paint paintDashed = null;

    private final int[] offset =    {10, 340 + (370-278)/2};
    private final int[] size =      {370, 278}; // aspect ratio 4:3

    private final long LENSLEECH_MAX_TIME_DIFF = 1000; // in ms

    private float angle = (float) Math.toRadians(10d); // rad
    private List<Rect> boundingBoxes = new ArrayList<Rect>();
    private LeechStatus leechStatus;

    // 640 x 480
    //private Scalar scale = new Scalar(3.27, 3.27);
    //private float[] offset = {-3, -240};

    // 1280 x 720
    // private Scalar scale = new Scalar(1.65, 1.65);
    // private float[] offset = {-10, -49};

    // 1920 x 1080
    // private Scalar scale = new Scalar(1.095, 1.095);
    // private float[] offset = {-5, -49};

    public DrawSurface(Context context) {
        super(context);
        this.context = context;
        init();
    }

    public DrawSurface(Context context, AttributeSet attrs) {
        super(context, attrs);
        this.context = context;
        init();
    }

    public DrawSurface(Context context, AttributeSet attrs, int defStyle) {
        super(context, attrs, defStyle);
        this.context = context;
        init();
    }

    private void init() {

        if (this.gestureDetector == null) {
            this.gestureDetector = new GestureDetector(this.context, (MainActivity) this.context);
            this.setClickable(true);
        }

        holder = getHolder();
        holder.addCallback(this);
        holder.setFormat(PixelFormat.TRANSPARENT);

        this.setZOrderOnTop(true);
        this.setWillNotDraw(false);

        paintWhite = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintWhite.setColor(Color.argb(255, 255, 255, 255));
        paintWhite.setStyle(Paint.Style.STROKE);
        paintWhite.setStrokeWidth(2.0f);

        paintGrey = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintGrey.setColor(Color.argb(255, 100, 100, 100));
        paintGrey.setStyle(Paint.Style.FILL_AND_STROKE);
        paintGrey.setStrokeWidth(2.0f);

        paintTranslucent = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintTranslucent.setColor(Color.argb(100, 255, 255, 255));
        paintTranslucent.setStyle(Paint.Style.STROKE);
        paintTranslucent.setStrokeWidth(2.0f);

        paintGreen = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintGreen.setColor(Color.argb(255, 0, 255, 0));
        paintGreen.setStyle(Paint.Style.STROKE);
        paintGreen.setStrokeWidth(2.0f);

        paintRed = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintRed.setColor(Color.RED);
        paintRed.setStyle(Paint.Style.STROKE);
        paintRed.setStrokeWidth(paintGreen.getStrokeWidth());

        paintShine = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintShine.setStyle(Paint.Style.STROKE);
        paintShine.setStrokeWidth(4.0f);
        paintShine.setColor(Color.argb(255, 0, 255, 0));
        paintShine.setStrokeCap(Paint.Cap.ROUND);
        paintShine.setStrokeJoin(Paint.Join.ROUND);

        paintBackground = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintBackground.setStyle(Paint.Style.FILL);
        paintBackground.setColor(Color.GRAY);

        paintFramelines = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintFramelines.setColor(Color.argb(255, 255, 255, 255));
        paintFramelines.setStyle(Paint.Style.STROKE);
        paintFramelines.setStrokeWidth(1.0f);

        paintText = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintText.setColor(Color.argb(255, 255, 255, 255));
//        paintText.setStyle(Paint.Style.STROKE);
//        paintText.setStrokeWidth(2.0f);
        paintText.setTextAlign(Paint.Align.RIGHT);
        paintText.setTextSize(25);

        paintTextCentered = new Paint(paintText);
        paintTextCentered.setTextAlign(Paint.Align.CENTER);
        paintTextCentered.setTextSize(25);

        paintSolidWhite = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintSolidWhite.setColor(Color.argb(255, 255, 255, 255));
        paintSolidWhite.setStrokeWidth(0f);

        paintSolidGreen = new Paint(paintSolidWhite);
        paintSolidGreen.setColor(Color.argb(255, 0, 255, 0));

        paintDashed = new Paint(Paint.ANTI_ALIAS_FLAG);
        paintDashed.setColor(Color.argb(255, 255, 255, 255));
        paintDashed.setStrokeWidth(2f);
        paintDashed.setStyle(Paint.Style.STROKE);
        paintDashed.setPathEffect(new DashPathEffect(new float[] {20f, 25f}, 0f));
    }

    public void setCallback(DrawSurfaceCallback onReadyCallback) {
        this.onReadyCallback = onReadyCallback;

        if (holder.getSurface().isValid()) onReadyCallback.onSurfaceReady(this);
    }

    public void setInteractive(boolean interative) {
        this.interactive = interative;
    }

    public void clearCanvas() throws Exception {
        if (!holder.getSurface().isValid()) {
            throw new Exception("surface not valid");
        }

        Canvas canvas = holder.lockCanvas();

        if (canvas == null) {
            throw new Exception("canvas not valid");
        }

        canvas.drawColor(Color.TRANSPARENT, PorterDuff.Mode.CLEAR);
        holder.unlockCanvasAndPost(canvas);
    }

    public void setAngle(float angle_deg) {
        if (Math.abs(angle_deg) <= 2.9) {
            this.angle = (float) Math.toRadians(0);
        } else {
            this.angle = (float) Math.toRadians(angle_deg);
        }
        invalidate();
    }

    public void setLeechStatus(LeechStatus leechStatus) {
        this.leechStatus = leechStatus;
    }

    public void setBoundingBoxes(List<Rect> boxes) {
        this.boundingBoxes = boxes;

        for (Rect r : this.boundingBoxes) {
            r.left = (int) ((float) r.left/CameraControllerX.ANALYZE_RESOLUTION.getWidth() * size[0] + offset[0]);
            r.right = (int) ((float) r.right/CameraControllerX.ANALYZE_RESOLUTION.getWidth() * size[0] + offset[0]);
            r.top = (int) ((float) r .top/CameraControllerX.ANALYZE_RESOLUTION.getHeight() * size[1] + offset[1]);
            r.bottom = (int) ((float) r.bottom/CameraControllerX.ANALYZE_RESOLUTION.getHeight() * size[1] + offset[1]);
        }

        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);

        // canvas.drawPaint(paintBackground);

        // BOUNDING BOXES
        for (Rect r : this.boundingBoxes) {
            canvas.drawRect(r, paintShine);
        }

        if (leechStatus != null) {
            Date now = new Date();
            long diff = now.getTime() - leechStatus.date.getTime();

            if (diff > LENSLEECH_MAX_TIME_DIFF) {
                leechStatus = null;
                drawLeech = false;
            } else {
                drawLeech = true;
                if (leechStatus.rotation != null) {

                    if (leechStatus.rotation >= 0 && leechStatus.rotation < Math.PI/3) {
                        drawFramelines = false;
                        drawAngle = false;
                    }

                    if (leechStatus.rotation >= Math.PI/3 && leechStatus.rotation < Math.PI/3*2) {
                        drawFramelines = true;
                        drawAngle = false;
                    }

                    if (leechStatus.rotation >= Math.PI/3*2 && leechStatus.rotation < Math.PI) {
                        drawFramelines = false;
                        drawAngle = true;
                    }
                }
            }
        }

        if (drawViewfinder) {

            // FRAME
            canvas.drawRect(
                    (float) offset[0], (float) offset[1],
                    (float) offset[0] + size[0], (float) offset[1] + size[1],
                    paintWhite
            );

            canvas.drawLine(540, 0, 540, getHeight(), paintDashed);

            // ANGLE
            if (drawAngle) {
                canvas.drawText("ANGLE:", (float) offset[0] + size[0] - 50, (float) offset[1] - 15, paintText);
                canvas.drawText(String.valueOf(Math.abs((int) Math.toDegrees(angle))), (float) offset[0] + size[0] - 5, (float) offset[1] - 15, paintText);

                canvas.drawLine(
                        (float) offset[0] + 20, (float) offset[1] + size[1] / 2f,
                        (float) offset[0] + size[0] - 20, (float) offset[1] + size[1] / 2f,
                        paintTranslucent
                );

                float centerX = offset[0] + size[0] / 2f;
                float centerY = offset[1] + size[1] / 2f;
                float width = size[0] / 2f - 20;
                float diffX = (float) Math.cos(angle) * width;
                float diffY = (float) Math.sin(angle) * width;

                Paint paint = paintGreen;
                if (Math.abs(angle) > 0.05) {
                    paint = paintRed;
                }
                canvas.drawLine(centerX - diffX, centerY - diffY,
                        centerX + diffX, centerY + diffY,
                        paint);
            }

            // COMPOSITING FRAMELINES
            if (drawFramelines) {
                canvas.drawLine(
                        offset[0] + size[0] * 0.33f, offset[1],
                        offset[0] + size[0] * 0.33f, offset[1] + size[1],
                        paintFramelines);
                canvas.drawLine(
                        offset[0] + size[0] * 0.66f, offset[1],
                        offset[0] + size[0] * 0.66f, offset[1] + size[1],
                        paintFramelines);
                canvas.drawLine(
                        offset[0], offset[1] + size[1] * 0.33f,
                        offset[0] + size[0], offset[1] + size[1] * 0.33f,
                        paintFramelines);
                canvas.drawLine(
                        offset[0], offset[1] + size[1] * 0.66f,
                        offset[0] + size[0], offset[1] + size[1] * 0.66f,
                        paintFramelines);
            }
        }

        if (drawLeech) {
            //canvas.drawCircle(offset[0] + size[0]/2, offset[1] + size[1] + 50, 200, paintFramelines);
            //canvas.drawArc(new RectF(offset[0]+50, offset[1]+size[1]-50, offset[0]+size[0]-50, offset[1]+size[1]+50), 0, -180, true, paintFramelines);

            canvas.drawRect(offset[0], offset[1] + size[1] + 10, offset[0] + size[0]/3*1 - 5, offset[1] + size[1] + 10 + 30, paintGrey);
            canvas.drawRect(offset[0] + size[0]/3*1 + 5, offset[1] + size[1] + 10, offset[0] + size[0]/3*2 -5, offset[1] + size[1] + 10 + 30, paintGrey);
            canvas.drawRect(offset[0] + size[0]/3*2 + 5, offset[1] + size[1] + 10, offset[0] + size[0], offset[1] + size[1] + 10 + 30, paintGrey);

            if (leechStatus != null && leechStatus.rotation != null){
                //float pos = (float) (0.5-Math.toDegrees(angle)/180) * size[0] % size[0];
                float pos = (float) (Math.toDegrees(leechStatus.rotation)/180) * size[0] % size[0];
                canvas.drawRect(offset[0] + Math.max(0, pos - 8), offset[1] + size[1] + 8, offset[0] + Math.min(size[0], pos + 8), offset[1] + size[1] + 10 + 30, paintSolidGreen);
            }

            canvas.drawText("CLEAR", (float) offset[0] + size[0]/6*1-3, (float) offset[1] + size[1] + 34, paintTextCentered);
            canvas.drawText("LINES", (float) offset[0] + size[0]/6*3, (float) offset[1] + size[1] + 34, paintTextCentered);
            canvas.drawText("LEVEL", (float) offset[0] + size[0]/6*5+3, (float) offset[1] + size[1] + 34, paintTextCentered);

        }

        if (drawIllumination) {

            if (android.os.Build.MODEL.equals("LG-H870")) { // LG G6
                canvas.drawCircle(-70, 1250, 270, paintSolidWhite);
                canvas.drawCircle(-70, 1250, 400, paintDashed);
            } else if (android.os.Build.MODEL.equals("Pixel 3a")) { // Pixel 3a
                canvas.drawCircle(-70, 890, 250, paintSolidWhite);
                canvas.drawCircle(-70, 890, 300, paintDashed);
            } else {
                // ...
            }
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        return this.gestureDetector.onTouchEvent(event);
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        if (onReadyCallback != null) {
            onReadyCallback.onSurfaceReady(this);
        }
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {

    }

    public static class DrawSurfaceCallback {

        public DrawSurfaceCallback() {
        }

        public void onSurfaceReady(DrawSurface surface) {

        }
    }
}
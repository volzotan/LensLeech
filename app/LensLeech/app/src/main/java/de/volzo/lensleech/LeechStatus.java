package de.volzo.lensleech;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.Serializable;
import java.util.Date;

public class LeechStatus implements Serializable {

    private final String MODE_ROTATION = "rotation";

    public Date date;

    public String mode;
    public Double rotation;
    public Boolean press;
    public Boolean squeeze;
    public Integer push;

    public LeechStatus(String json) throws Exception {

        this.date = new Date();

        JSONObject mainObj = new JSONObject(json);

        this.mode = mainObj.getString("mode");

        if (!mainObj.isNull("rotation")) {
            this.rotation = mainObj.getDouble("rotation");
        }

        if (!mainObj.isNull("press")) {
            this.press = mainObj.getBoolean("press");
        }

        // JSONObject pressValues = mainObj.getJSONObject("press_values");

        if (!mainObj.isNull("squeeze")) {
            this.squeeze = mainObj.getBoolean("squeeze");
        }

        if (!mainObj.isNull("push")) {
            this.push = mainObj.getInt("push");
        }

        // JSONArray foundPatterns     = mainObj.getJSONArray("found_patterns");
        // JSONArray missingPatterns   = mainObj.getJSONArray("missing_patterns");

    }

}

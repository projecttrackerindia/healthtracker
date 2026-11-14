package in.urbanhealth.twa;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;

/**
 * The app's front door. Picks how the web app runs on this phone:
 *  - Chrome installed and enabled: full-screen in Chrome (Trusted Web Activity), so sign-in, notifications and camera
 *    behave exactly as on the web.
 *  - otherwise, or after Chrome handed back a blank screen twice on this phone: our own in-app view (WebActivity).
 * Phone makers' own browsers (vivo, Xiaomi, OPPO) are never used: several claim to run these apps and then show a
 * white screen and close, which is what a vivo phone did with 1.0.1.
 */
public class Start extends Activity {
    static final String[] CHROMES = {"com.android.chrome", "com.chrome.beta", "com.chrome.dev", "com.chrome.canary"};
    static final String PREFS = "uh-launch";

    static String chrome(PackageManager pm) {
        for (String p : CHROMES) {
            try {
                ApplicationInfo ai = pm.getApplicationInfo(p, 0);
                if (ai.enabled) return p;
            } catch (PackageManager.NameNotFoundException ignored) { }
        }
        return null;
    }

    static SharedPreferences prefs(Context c) { return c.getSharedPreferences(PREFS, MODE_PRIVATE); }

    static boolean useWeb(Context c) {
        return chrome(c.getPackageManager()) == null || prefs(c).getInt("blank", 0) >= 2;
    }

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        Intent in = getIntent();
        Intent next = new Intent(this, useWeb(this) ? WebActivity.class : Twa.class);
        if (in != null) {
            next.setAction(in.getAction());
            next.setData(in.getData());
            if (in.getExtras() != null) next.putExtras(in.getExtras());
        }
        startActivity(next);
        finish();
        overridePendingTransition(0, 0);
    }
}

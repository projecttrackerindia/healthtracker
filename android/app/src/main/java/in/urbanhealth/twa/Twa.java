package in.urbanhealth.twa;

import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;

import com.google.androidbrowserhelper.trusted.LauncherActivity;
import com.google.androidbrowserhelper.trusted.TwaLauncher;

/** Runs the app in Chrome, never in another browser; if Chrome comes straight back, opens the in-app view instead. */
public class Twa extends LauncherActivity {
    private long started;

    @Override
    protected void onCreate(Bundle b) {
        started = SystemClock.elapsedRealtime();
        super.onCreate(b);
    }

    @Override
    protected TwaLauncher createTwaLauncher() {
        String p = Start.chrome(getPackageManager());
        return p != null ? new TwaLauncher(this, p) : new TwaLauncher(this);
    }

    @Override
    protected void onRestart() {
        // Chrome normally keeps the app open for minutes. Back here within a few seconds means it showed nothing.
        boolean blank = SystemClock.elapsedRealtime() - started < 4000;
        Start.prefs(this).edit().putInt("blank", blank ? Start.prefs(this).getInt("blank", 0) + 1 : 0).apply();
        super.onRestart();   // closes this screen, as it always did
        if (blank) {
            Intent w = new Intent(this, WebActivity.class);
            w.setData(getLaunchingUrl());
            startActivity(w);
            overridePendingTransition(0, 0);
        }
    }
}

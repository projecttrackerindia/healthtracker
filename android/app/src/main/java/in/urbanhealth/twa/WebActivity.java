package in.urbanhealth.twa;

import android.Manifest;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.view.View;
import android.view.Window;
import android.webkit.CookieManager;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * The in-app view, for phones without Chrome or where Chrome cannot run the app full-screen.
 * Only urbanhealth.in opens inside; every other link (maps, UPI, phone calls, WhatsApp, other sites) goes to the phone.
 * Camera, location and microphone are asked for only when a page asks for them, the way a browser would.
 */
public class WebActivity extends Activity {
    private static final int REQ_FILE = 11, REQ_PERM_CAMERA_FILE = 12, REQ_PERM_GEO = 13, REQ_PERM_MEDIA = 14;
    private WebView web;
    private ValueCallback<Uri[]> fileCb;
    private WebChromeClient.FileChooserParams fileParams;
    private Uri photoUri;
    private String geoOrigin;
    private GeolocationPermissions.Callback geoCb;
    private PermissionRequest mediaReq;

    private String host() { return getString(R.string.web_host); }

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        Window w = getWindow();
        w.setStatusBarColor(Color.parseColor("#F5F5F7"));
        w.setNavigationBarColor(Color.parseColor("#F5F5F7"));
        if (Build.VERSION.SDK_INT >= 23) w.getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);

        web = new WebView(this);
        web.setBackgroundColor(Color.parseColor("#F5F5F7"));
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setGeolocationEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setSupportMultipleWindows(false);
        s.setUserAgentString(s.getUserAgentString() + " UrbanHealthAndroid/" + BuildConfig.VERSION_NAME);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                if ("https".equals(u.getScheme()) && host().equalsIgnoreCase(u.getHost())) return false;
                openOutside(u);
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCb != null) fileCb.onReceiveValue(null);
                fileCb = cb;
                fileParams = p;
                if (wantsCamera(p) && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{Manifest.permission.CAMERA}, REQ_PERM_CAMERA_FILE);
                } else {
                    pickFile();
                }
                return true;
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback cb) {
                if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                    cb.invoke(origin, true, false);
                } else {
                    geoOrigin = origin;
                    geoCb = cb;
                    requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_PERM_GEO);
                }
            }

            @Override
            public void onPermissionRequest(PermissionRequest r) {
                if (!host().equalsIgnoreCase(r.getOrigin().getHost())) { r.deny(); return; }
                List<String> need = new ArrayList<>();
                for (String res : r.getResources()) {
                    if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(res)) need.add(Manifest.permission.CAMERA);
                    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(res)) need.add(Manifest.permission.RECORD_AUDIO);
                }
                List<String> missing = new ArrayList<>();
                for (String p : need) if (checkSelfPermission(p) != PackageManager.PERMISSION_GRANTED) missing.add(p);
                if (missing.isEmpty()) { r.grant(r.getResources()); return; }
                mediaReq = r;
                requestPermissions(missing.toArray(new String[0]), REQ_PERM_MEDIA);
            }
        });
        web.setDownloadListener((url, ua, disposition, mime, length) -> {
            try {
                DownloadManager.Request q = new DownloadManager.Request(Uri.parse(url));
                q.addRequestHeader("Cookie", CookieManager.getInstance().getCookie(url));
                q.addRequestHeader("User-Agent", ua);
                q.setMimeType(mime);
                String name = URLUtil.guessFileName(url, disposition, mime);
                q.setTitle(name);
                q.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                q.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name);
                ((DownloadManager) getSystemService(DOWNLOAD_SERVICE)).enqueue(q);
                Toast.makeText(this, "Downloading " + name, Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                openOutside(Uri.parse(url));
            }
        });

        if (b != null) web.restoreState(b);
        else web.loadUrl(startUrl(getIntent()));
    }

    private String startUrl(Intent in) {
        Uri d = in != null ? in.getData() : null;
        if (d != null && "https".equals(d.getScheme()) && host().equalsIgnoreCase(d.getHost())) return d.toString();
        return getString(R.string.web_start);
    }

    @Override
    protected void onNewIntent(Intent in) {
        super.onNewIntent(in);
        if (in != null && in.getData() != null) web.loadUrl(startUrl(in));
    }

    private void openOutside(Uri u) {
        try {
            Intent i = "intent".equals(u.getScheme()) ? Intent.parseUri(u.toString(), Intent.URI_INTENT_SCHEME) : new Intent(Intent.ACTION_VIEW, u);
            i.addCategory(Intent.CATEGORY_BROWSABLE);
            i.setComponent(null);
            i.setSelector(null);
            startActivity(i);
        } catch (Exception e) {
            Toast.makeText(this, "No app on this phone can open that link.", Toast.LENGTH_SHORT).show();
        }
    }

    private static boolean wantsCamera(WebChromeClient.FileChooserParams p) {
        if (p.isCaptureEnabled()) return true;
        for (String t : p.getAcceptTypes()) if (t != null && t.startsWith("image")) return true;
        return false;
    }

    private void pickFile() {
        Intent pick;
        try { pick = fileParams.createIntent(); } catch (Exception e) { pick = new Intent(Intent.ACTION_GET_CONTENT).setType("*/*"); }
        pick.addCategory(Intent.CATEGORY_OPENABLE);
        Intent chooser = Intent.createChooser(pick, "Add a photo or file");
        photoUri = null;
        if (wantsCamera(fileParams) && checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            try {
                File dir = new File(getCacheDir(), "camera");
                if (!dir.exists()) dir.mkdirs();
                File f = File.createTempFile("photo_", ".jpg", dir);
                photoUri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", f);
                Intent cam = new Intent(MediaStore.ACTION_IMAGE_CAPTURE).putExtra(MediaStore.EXTRA_OUTPUT, photoUri)
                        .addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                if (fileParams.isCaptureEnabled()) chooser = cam;
                else chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{cam});
            } catch (Exception ignored) { photoUri = null; }
        }
        try {
            startActivityForResult(chooser, REQ_FILE);
        } catch (ActivityNotFoundException e) {
            fileCb.onReceiveValue(null);
            fileCb = null;
        }
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req != REQ_FILE || fileCb == null) return;
        Uri[] out = null;
        if (res == RESULT_OK) {
            if (data != null && (data.getData() != null || data.getClipData() != null)) {
                out = WebChromeClient.FileChooserParams.parseResult(res, data);
            } else if (photoUri != null) {
                out = new Uri[]{photoUri};
            }
        }
        fileCb.onReceiveValue(out);
        fileCb = null;
    }

    @Override
    public void onRequestPermissionsResult(int req, String[] perms, int[] grants) {
        super.onRequestPermissionsResult(req, perms, grants);
        boolean ok = grants.length > 0;
        for (int g : grants) ok &= g == PackageManager.PERMISSION_GRANTED;
        if (req == REQ_PERM_CAMERA_FILE && fileCb != null) {
            pickFile();   // with the camera if allowed, otherwise gallery and files only
        } else if (req == REQ_PERM_GEO && geoCb != null) {
            boolean any = false;
            for (int g : grants) any |= g == PackageManager.PERMISSION_GRANTED;
            geoCb.invoke(geoOrigin, any, false);
            geoCb = null;
        } else if (req == REQ_PERM_MEDIA && mediaReq != null) {
            if (ok) mediaReq.grant(mediaReq.getResources()); else mediaReq.deny();
            mediaReq = null;
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}

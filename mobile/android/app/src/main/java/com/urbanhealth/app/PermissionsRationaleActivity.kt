package com.urbanhealth.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

/** Health Connect opens this when the person asks why the app wants health data: we show the privacy policy. */
class PermissionsRationaleActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://urbanhealth.in/privacy")))
        finish()
    }
}

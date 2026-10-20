package com.thehealthtracker.app

import android.Manifest
import android.content.Intent
import android.net.Uri
import com.getcapacitor.JSObject
import com.getcapacitor.PermissionState
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PermissionCallback

/**
 * Sos.call({number}) places the call at once (ACTION_CALL) when CALL_PHONE is granted; the first time it asks, then
 * dials. Without the permission it falls back to the dialer with the number ready (ACTION_DIAL), which never fails.
 * The web app asks for the permission from the Safety set-up card, so the emergency moment has no prompt.
 */
@CapacitorPlugin(name = "Sos", permissions = [Permission(strings = [Manifest.permission.CALL_PHONE], alias = "call")])
class SosPlugin : Plugin() {

    @PluginMethod
    fun prepare(call: PluginCall) {
        if (getPermissionState("call") == PermissionState.GRANTED) {
            call.resolve(JSObject().put("granted", true)); return
        }
        requestPermissionForAlias("call", call, "onPrepare")
    }

    @PermissionCallback
    private fun onPrepare(call: PluginCall) {
        call.resolve(JSObject().put("granted", getPermissionState("call") == PermissionState.GRANTED))
    }

    @PluginMethod
    fun call(call: PluginCall) {
        val number = (call.getString("number") ?: "").filter { it.isDigit() || it == '+' }
        if (number.isEmpty()) { call.reject("number required"); return }
        val uri = Uri.parse("tel:$number")
        try {
            if (getPermissionState("call") == PermissionState.GRANTED) {
                activity.startActivity(Intent(Intent.ACTION_CALL, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                call.resolve(JSObject().put("how", "auto")); return
            }
        } catch (e: Exception) { /* fall through to the dialer */ }
        activity.startActivity(Intent(Intent.ACTION_DIAL, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        call.resolve(JSObject().put("how", "dialer"))
    }
}

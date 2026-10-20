package com.thehealthtracker.app

import android.content.Intent
import androidx.activity.result.ActivityResult
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.BloodGlucoseRecord
import androidx.health.connect.client.records.BloodPressureRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.OxygenSaturationRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.records.WeightRecord
import androidx.health.connect.client.request.AggregateGroupByPeriodRequest
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.getcapacitor.JSArray
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.ActivityCallback
import com.getcapacitor.annotation.CapacitorPlugin
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.LocalDate
import java.time.Period
import java.time.ZoneId
import java.time.temporal.ChronoUnit

/**
 * Reads the phone's Health Connect store (where Samsung Health, Google Fit, Noise, boAt, Fitbit, Garmin and others
 * write) and hands the web app plain JSON. Nothing is written back; the web app saves what it keeps.
 *
 *   HealthSync.available()            -> {available, needsUpdate}
 *   HealthSync.requestPermissions()   -> {granted: [..]}
 *   HealthSync.read({days})           -> {steps:[{d,n}], sleep:[{d,min}], hr:[{t,bpm}], weight:[{t,kg}],
 *                                         bp:[{t,sys,dia}], glucose:[{t,mgdl}], spo2:[{t,pct}]}
 */
@CapacitorPlugin(name = "HealthSync")
class HealthSyncPlugin : Plugin() {
    private val scope = CoroutineScope(Dispatchers.IO)
    private val permissions = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(WeightRecord::class),
        HealthPermission.getReadPermission(BloodPressureRecord::class),
        HealthPermission.getReadPermission(BloodGlucoseRecord::class),
        HealthPermission.getReadPermission(OxygenSaturationRecord::class)
    )

    @PluginMethod
    fun available(call: PluginCall) {
        val status = HealthConnectClient.getSdkStatus(context)
        val out = JSObject()
        out.put("available", status == HealthConnectClient.SDK_AVAILABLE)
        out.put("needsUpdate", status == HealthConnectClient.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED)
        call.resolve(out)
    }

    @PluginMethod
    override fun requestPermissions(call: PluginCall) {
        if (HealthConnectClient.getSdkStatus(context) != HealthConnectClient.SDK_AVAILABLE) {
            call.reject("Health Connect is not available on this phone"); return
        }
        val client = HealthConnectClient.getOrCreate(context)
        scope.launch {
            val granted = client.permissionController.getGrantedPermissions()
            if (granted.containsAll(permissions)) {
                call.resolve(grantedJson(granted)); return@launch
            }
            val contract = PermissionController.createRequestPermissionResultContract()
            val intent: Intent = contract.createIntent(context, permissions)
            activity.runOnUiThread { startActivityForResult(call, intent, "onPermissionResult") }
        }
    }

    @ActivityCallback
    fun onPermissionResult(call: PluginCall?, result: ActivityResult) {
        if (call == null) return
        val client = HealthConnectClient.getOrCreate(context)
        scope.launch {
            val granted = client.permissionController.getGrantedPermissions()
            call.resolve(grantedJson(granted))
        }
    }

    private fun grantedJson(granted: Set<String>): JSObject {
        val out = JSObject()
        val arr = JSArray()
        granted.forEach { arr.put(it.substringAfterLast('.')) }
        out.put("granted", arr)
        out.put("all", granted.containsAll(permissions))
        return out
    }

    @PluginMethod
    fun read(call: PluginCall) {
        if (HealthConnectClient.getSdkStatus(context) != HealthConnectClient.SDK_AVAILABLE) {
            call.reject("Health Connect is not available on this phone"); return
        }
        val days = (call.getInt("days") ?: 7).coerceIn(1, 90)
        val client = HealthConnectClient.getOrCreate(context)
        val zone = ZoneId.systemDefault()
        val end = Instant.now()
        val start = end.minus(days.toLong(), ChronoUnit.DAYS)
        val range = TimeRangeFilter.between(start, end)
        scope.launch {
            try {
                val out = JSObject()
                // steps per day
                val steps = JSArray()
                val startDay = LocalDate.now(zone).minusDays(days.toLong() - 1).atStartOfDay()
                val stepAgg = client.aggregateGroupByPeriod(
                    AggregateGroupByPeriodRequest(setOf(StepsRecord.COUNT_TOTAL), TimeRangeFilter.between(startDay, LocalDate.now(zone).plusDays(1).atStartOfDay()), Period.ofDays(1))
                )
                for (b in stepAgg) {
                    val n = b.result[StepsRecord.COUNT_TOTAL] ?: 0L
                    val o = JSObject(); o.put("d", b.startTime.toLocalDate().toString()); o.put("n", n); steps.put(o)
                }
                out.put("steps", steps)
                // sleep sessions → minutes per night (by end date)
                val sleep = JSArray()
                val sessions = client.readRecords(ReadRecordsRequest(SleepSessionRecord::class, range)).records
                val byDay = HashMap<String, Long>()
                for (s in sessions) {
                    val d = s.endTime.atZone(zone).toLocalDate().toString()
                    byDay[d] = (byDay[d] ?: 0L) + ChronoUnit.MINUTES.between(s.startTime, s.endTime)
                }
                byDay.toSortedMap().forEach { (d, min) -> val o = JSObject(); o.put("d", d); o.put("min", min); sleep.put(o) }
                out.put("sleep", sleep)
                // heart rate: last sample of each series, newest 60
                val hr = JSArray()
                client.readRecords(ReadRecordsRequest(HeartRateRecord::class, range)).records.takeLast(60).forEach { r ->
                    r.samples.lastOrNull()?.let { smp -> val o = JSObject(); o.put("t", smp.time.toEpochMilli()); o.put("bpm", smp.beatsPerMinute); hr.put(o) }
                }
                out.put("hr", hr)
                val weight = JSArray()
                client.readRecords(ReadRecordsRequest(WeightRecord::class, range)).records.takeLast(30).forEach { r ->
                    val o = JSObject(); o.put("t", r.time.toEpochMilli()); o.put("kg", Math.round(r.weight.inKilograms * 10.0) / 10.0); weight.put(o)
                }
                out.put("weight", weight)
                val bp = JSArray()
                client.readRecords(ReadRecordsRequest(BloodPressureRecord::class, range)).records.takeLast(60).forEach { r ->
                    val o = JSObject(); o.put("t", r.time.toEpochMilli()); o.put("sys", Math.round(r.systolic.inMillimetersOfMercury)); o.put("dia", Math.round(r.diastolic.inMillimetersOfMercury)); bp.put(o)
                }
                out.put("bp", bp)
                val glu = JSArray()
                client.readRecords(ReadRecordsRequest(BloodGlucoseRecord::class, range)).records.takeLast(60).forEach { r ->
                    val o = JSObject(); o.put("t", r.time.toEpochMilli()); o.put("mgdl", Math.round(r.level.inMilligramsPerDeciliter)); glu.put(o)
                }
                out.put("glucose", glu)
                val spo2 = JSArray()
                client.readRecords(ReadRecordsRequest(OxygenSaturationRecord::class, range)).records.takeLast(60).forEach { r ->
                    val o = JSObject(); o.put("t", r.time.toEpochMilli()); o.put("pct", Math.round(r.percentage.value)); spo2.put(o)
                }
                out.put("spo2", spo2)
                call.resolve(out)
            } catch (e: Exception) {
                call.reject(e.message ?: "Could not read Health Connect")
            }
        }
    }
}

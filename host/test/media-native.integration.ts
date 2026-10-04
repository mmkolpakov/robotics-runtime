import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Context } from 'cordis';
import { mkdtemp, writeFile, readFile, mkdir, copyFile, stat, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { Jobs } from '../src/plugins/jobs/index.js';
import { MediaEndpoint } from '../src/plugins/media-endpoint/index.js';
test('native GI worker observes EOS, error, cancellation and NULL cleanup without forwarding frames', { timeout: 15000 }, async () => {
  const directory = await mkdtemp(join(tmpdir(), 'rr-gst-'));
  const ctx = new Context(); await ctx.plugin(Jobs, { timeoutMs: 10000, killTimeoutMs: 2000 });
  await ctx.plugin(MediaEndpoint, { deadlineMs: 1000, producerPath: '/workspace/producers/media_worker.py',
    command: { executable: '/usr/bin/podman', prefixArgs: ['run', '--rm', '--init', '--init-path', resolve('.tools/tini'),
      '--userns=keep-id:uid=1000,gid=1000', '--user', '1000:1000', '-v', resolve('.') + ':/workspace:ro', '-v', directory + ':' + directory,
      '--entrypoint', 'python3', 'localhost/rr-c-media:c12-locked'],
      env: { PATH: '/usr/local/bin:/usr/bin:/bin', HOME: '/home/dev', USER: 'dev', LOGNAME: 'dev', DBUS_SESSION_BUS_ADDRESS: 'unix:path=/run/user/' + process.getuid!() + '/bus', XDG_RUNTIME_DIR: '/run/user/' + process.getuid!() } } });
  try {
    const config = join(directory, 'eos.json'); const payload = join(directory, 'frames.rgb');
    await writeFile(config, JSON.stringify({ pipeline: 'videotestsrc num-buffers=3 ! video/x-raw,format=RGB,width=64,height=48 ! filesink location=' + payload }));
    const eos = await ctx.mediaEndpoint.capture({ configPath: config, reportPath: join(directory, 'eos-report.json') });
    assert.equal(eos.status, 'passed', eos.job.stderr + eos.diagnostic);
    assert.match(eos.report?.gstreamer ?? '', /1.24.2/);
    assert.equal((await stat(payload)).size, 64 * 48 * 3 * 3);
    assert.equal(typeof eos.report?.position?.value, 'string');
    const invalid = join(directory, 'missing.json');
    await writeFile(invalid, JSON.stringify({ pipeline: 'filesrc location=/missing/c12-input ! fakesink' }));
    const error = await ctx.mediaEndpoint.capture({ configPath: invalid, reportPath: join(directory, 'error-report.json') });
    assert.equal(error.status, 'error'); assert.ok(error.report?.events.some(event => event.type === 'error'));
    assert.equal(error.report?.cleanup.observed, 'null');
    const forever = join(directory, 'forever.json');
    await writeFile(forever, JSON.stringify({ pipeline: 'videotestsrc is-live=true ! fakesink' }));
    const timed = await ctx.mediaEndpoint.capture({ configPath: forever, reportPath: join(directory, 'timeout-report.json') });
    assert.equal(timed.status, 'error'); assert.equal(timed.report?.status, 'timeout'); assert.equal(timed.report?.cleanup.succeeded, true);
    const readyPath = join(directory, 'ready.json');
    const abort = new AbortController();
    const waiting = ctx.mediaEndpoint.capture({ configPath: forever, reportPath: join(directory, 'cancel-report.json'),
      readyMarkerPath: readyPath, cancelSignal: abort.signal });
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt++) {
      try { ready = JSON.parse(await readFile(readyPath, 'utf8')).playing === true; if (ready) break; } catch {}
      await new Promise(done => setTimeout(done, 20));
    }
    assert.equal(ready, true, 'cancellation follows actual native PLAYING observation');
    abort.abort();
    const canceled = await waiting;
    assert.equal(canceled.status, 'error'); assert.equal(canceled.job.canceled, true);
    assert.equal(canceled.report?.status, 'canceled'); assert.equal(canceled.report?.cleanup.observed, 'null');
    const artifacts = resolve('../artifacts/host/c12');
    await mkdir(artifacts, { recursive: true });
    await copyFile(payload, join(artifacts, 'synthetic-frames.rgb'));
    for (const name of ['eos', 'error', 'timeout', 'cancel']) await copyFile(join(directory, name + '-report.json'), join(artifacts, 'gst-' + name + '.json'));
    console.log(JSON.stringify({ synthetic_capture_bytes: (await stat(payload)).size, eos: eos.report, error: error.report, timeout: timed.report,
      cancellation_report: canceled.report, cancellation_status: canceled.status, camera_or_RTSP_qualified: false }));
  } finally { await ctx.fiber.dispose(); await rm(directory, { recursive: true, force: true }); }
});

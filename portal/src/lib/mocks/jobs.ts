import type { JobState, JobPhase } from '../types'

const LOG_LINES: Record<JobPhase, string[]> = {
  aoi_validation: [
    '[INFO] AOI geometry received: POLYGON',
    '[INFO] Validating area bounds...',
    '[INFO] Area: 45.0 feddan (189,037 m²)',
    '[INFO] AOI within Egypt bounds ✓',
    '[INFO] AOI validation complete',
  ],
  satellite_fetch: [
    '[INFO] Querying Planetary Computer STAC catalog...',
    '[INFO] Search window: 2022-03-01 → 2024-03-01',
    '[INFO] Collection: sentinel-2-l2a',
    '[INFO] Found 52 scenes in search window',
    '[INFO] Cloud filter (< 30%): 41 scenes retained',
    '[INFO] Downloading 41 scenes...',
    '[INFO] Download complete: 41 scenes',
  ],
  vegetation_analysis: [
    '[INFO] Computing NDVI for 41 scenes...',
    '[INFO] Computing EVI for 41 scenes...',
    '[INFO] Applying cloud mask from SCL band...',
    '[INFO] Building NDVI time series...',
    '[INFO] Trend analysis: Mann-Kendall test...',
    '[INFO] Vegetation analysis complete',
  ],
  risk_modeling: [
    '[INFO] Loading scoring rules v2.1...',
    '[INFO] Evaluating land status...',
    '[INFO] Evaluating 2-year trend...',
    '[INFO] Running risk flag checks...',
    '[INFO] Computing confidence score...',
    '[INFO] Risk modeling complete',
  ],
  report_generation: [
    '[INFO] Generating report summary...',
    '[INFO] Compiling evidence package...',
    '[INFO] Report generation complete',
    '[INFO] Analysis succeeded',
  ],
}

export function getMockJob(id: string): JobState {
  const seedNum = parseInt(id.replace(/\D/g, '').slice(-3) || '1', 10)
  const isProcessing = id.includes('008') || id.includes('009')
  const isQueued = id.includes('010') || id.includes('011')
  const isFailed = id.includes('012')

  if (isQueued) {
    return { id, land_id: id.replace('job', 'land'), status: 'queued', progress: 0, logs: ['[INFO] Job queued, waiting for worker...'] }
  }

  if (isFailed) {
    return {
      id, land_id: id.replace('job', 'land'), status: 'failed', progress: 35, phase: 'satellite_fetch',
      started_at: new Date(Date.now() - 3600000).toISOString(),
      error: 'Satellite data fetch timeout: no scenes available for AOI in requested window',
      logs: [...LOG_LINES.aoi_validation, ...LOG_LINES.satellite_fetch.slice(0, 4), '[ERROR] Fetch timeout after 60s'],
    }
  }

  if (isProcessing) {
    const elapsedMs = Date.now() - (seedNum * 1000000 % 120000)
    const progress = Math.min(75, Math.max(10, (elapsedMs / 1000) % 75))
    const phaseIdx = Math.floor(progress / 20)
    const phases: JobPhase[] = ['aoi_validation', 'satellite_fetch', 'vegetation_analysis', 'risk_modeling', 'report_generation']
    const phase = phases[Math.min(phaseIdx, 3)]
    const logs = phases.slice(0, phaseIdx).flatMap(p => LOG_LINES[p])

    return {
      id, land_id: id.replace('job', 'land'), status: 'running', progress: Math.round(progress),
      phase, started_at: new Date(Date.now() - elapsedMs).toISOString(), logs,
    }
  }

  return {
    id, land_id: id.replace('job', 'land'), status: 'succeeded', progress: 100,
    phase: 'report_generation',
    started_at: new Date(Date.now() - 480000).toISOString(),
    completed_at: new Date(Date.now() - 60000).toISOString(),
    logs: Object.values(LOG_LINES).flat(),
  }
}

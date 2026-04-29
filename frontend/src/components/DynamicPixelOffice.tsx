import { type CSSProperties, useEffect, useMemo, useState } from "react";

import type { SimulationAgentRole, SimulationStep } from "../lib/graphSimulator";

type Props = {
  currentStep: SimulationStep;
  reducedMotion: boolean;
  running: boolean;
};

type Facing = "front" | "back" | "left" | "right";

type AgentPosition = {
  x: number;
  y: number;
  facing: Facing;
};

type AgentConfig = {
  role: SimulationAgentRole;
  title: string;
  name: string;
  spritePath: string;
  home: AgentPosition;
};

const SPRITE_FRAME_MS = 150;
const SPRITE_FRAME_SIZE = 64;

const rowByFacing: Record<Facing, number> = {
  front: 0,
  back: 1,
  right: 2,
  left: 3,
};

const agents: AgentConfig[] = [
  {
    role: "data_analyst",
    title: "Data Analyst",
    name: "Aline",
    spritePath: "/assets/sprites/agent_a.png",
    home: { x: 184, y: 345, facing: "back" },
  },
  {
    role: "reviewer",
    title: "Reviewer",
    name: "Ravi",
    spritePath: "/assets/sprites/agent_b.png",
    home: { x: 394, y: 345, facing: "back" },
  },
  {
    role: "ml_executor",
    title: "ML Executor",
    name: "Mila",
    spritePath: "/assets/sprites/agent_c.png",
    home: { x: 595, y: 345, facing: "back" },
  },
  {
    role: "recommendation_engine",
    title: "Recommendation",
    name: "Nico",
    spritePath: "/assets/sprites/agent_d.png",
    home: { x: 805, y: 345, facing: "back" },
  },
  {
    role: "explainability",
    title: "Explainability",
    name: "Sofia",
    spritePath: "/assets/sprites/agent_s.png",
    home: { x: 1015, y: 345, facing: "back" },
  },
];

const officePositionsByPhase: Partial<
  Record<SimulationStep["office"]["phase"], Partial<Record<SimulationAgentRole, AgentPosition>>>
> = {
  "quality-gate": {
    data_analyst: { x: 370, y: 345, facing: "right" },
    reviewer: { x: 394, y: 345, facing: "left" },
  },
  analysis: {
    data_analyst: { x: 370, y: 345, facing: "right" },
    reviewer: { x: 394, y: 345, facing: "left" },
  },
  "model-run": {
    data_analyst: { x: 560, y: 345, facing: "right" },
    ml_executor: { x: 595, y: 345, facing: "left" },
  },
  recommendation: {
    ml_executor: { x: 770, y: 345, facing: "right" },
    recommendation_engine: { x: 805, y: 345, facing: "left" },
  },
  explainability: {
    recommendation_engine: { x: 975, y: 345, facing: "right" },
    explainability: { x: 1015, y: 345, facing: "left" },
  },
  review: {
    explainability: { x: 440, y: 345, facing: "left" },
    reviewer: { x: 394, y: 345, facing: "right" },
  },
  release: {
    // All 5 agents positioned to show the full pipeline state during release
    data_analyst: { x: 970, y: 345, facing: "right" },      // Publishing at supervisor desk
    reviewer: { x: 1015, y: 345, facing: "left" },          // Approving at supervisor desk
    ml_executor: { x: 595, y: 345, facing: "back" },        // At own desk, work complete
    recommendation_engine: { x: 805, y: 345, facing: "back" }, // At own desk, work complete
    explainability: { x: 184, y: 345, facing: "back" },     // Moved to planner desk area
  },
  complete: {
    // Spread out more to avoid label/speech bubble overlap (was 70px apart, now 100px)
    data_analyst: { x: 380, y: 400, facing: "right" },
    reviewer: { x: 480, y: 400, facing: "right" },
    ml_executor: { x: 580, y: 400, facing: "front" },
    recommendation_engine: { x: 680, y: 400, facing: "left" },
    explainability: { x: 780, y: 400, facing: "left" },
  },
};

function getAgentPosition(agent: AgentConfig, step: SimulationStep): AgentPosition {
  return officePositionsByPhase[step.office.phase]?.[agent.role] ?? agent.home;
}

function buildSpriteStyle(agent: AgentConfig, position: AgentPosition, frame: number): CSSProperties {
  const row = rowByFacing[position.facing];
  return {
    backgroundImage: `url(${agent.spritePath})`,
    backgroundPosition: `-${frame * SPRITE_FRAME_SIZE}px -${row * SPRITE_FRAME_SIZE}px`,
  };
}

// Desk layout: 5 desks evenly spaced across the 1200px scene
const DESK_W = 250;
const DESK_H = 170;
const desks = [
  { deskX: 55, deskY: 195, chairX: 159, chairY: 280, monitorX: 117, monitorY: 218, mugX: 185, mugY: 238 },
  { deskX: 260, deskY: 195, chairX: 364, chairY: 280, monitorX: 323, monitorY: 222, mugX: 400, mugY: 240 },
  { deskX: 465, deskY: 195, chairX: 569, chairY: 280, monitorX: 523, monitorY: 218, mugX: 590, mugY: 238 },
  { deskX: 670, deskY: 195, chairX: 774, chairY: 280, monitorX: 733, monitorY: 222, mugX: 810, mugY: 240 },
  { deskX: 875, deskY: 195, chairX: 979, chairY: 280, monitorX: 910, monitorY: 218, mugX: 980, mugY: 238 },
];

const stars = [
  { left: 60, top: 38, size: 3 },
  { left: 180, top: 55, size: 4 },
  { left: 350, top: 35, size: 3 },
  { left: 500, top: 42, size: 3 },
  { left: 650, top: 50, size: 4 },
  { left: 820, top: 38, size: 3 },
  { left: 950, top: 48, size: 3 },
  { left: 1100, top: 40, size: 4 },
  { left: 130, top: 22, size: 2 },
  { left: 290, top: 60, size: 2 },
  { left: 420, top: 15, size: 3 },
  { left: 580, top: 68, size: 2 },
  { left: 720, top: 25, size: 2 },
  { left: 870, top: 55, size: 3 },
  { left: 1030, top: 18, size: 2 },
  { left: 1140, top: 45, size: 2 },
  { left: 40, top: 50, size: 2 },
  { left: 460, top: 42, size: 2 },
];

export default function DynamicPixelOffice({ currentStep, reducedMotion, running }: Props) {
  const [frame, setFrame] = useState(0);

  const activeAgents = useMemo(
    () => new Set(currentStep.office.activeAgents),
    [currentStep.office.activeAgents],
  );

  useEffect(() => {
    if (reducedMotion || !running) {
      setFrame(0);
      return;
    }

    const interval = window.setInterval(() => {
      setFrame((current) => (current + 1) % 8);
    }, SPRITE_FRAME_MS);

    return () => window.clearInterval(interval);
  }, [reducedMotion, running]);

  const isAgentActive = (role: SimulationAgentRole) => activeAgents.has(role);

  // Check if ping pong has 2+ agents nearby (idle agents at ping pong spots)
  const pingPongActive = false; // Would need idle position tracking to implement fully

  // Check if anyone is at the hookah
  const hookahActive = false; // Would need idle position tracking to implement fully

  const tickerText = `/// AGROPREDICT AI /// ${currentStep.office.phase.toUpperCase()} /// ${currentStep.office.label.toUpperCase()} /// AGENTS: 5 /// PREDICTION PIPELINE /// `;

  return (
    <section
      className={reducedMotion ? "pixel-office reduced-office-motion" : "pixel-office"}
      aria-label={`Agriculture logistics operations room: ${currentStep.office.label}`}
    >
      <div className="pixel-office-copy">
        <p className="eyebrow">{currentStep.office.phase}</p>
        <h3>{currentStep.office.label}</h3>
        <p>{currentStep.office.interaction}</p>
      </div>

      <div className="pixel-office-scene pixel-office-scene-v2" role="list" aria-label="Prediction agent operations positions">
        {/* === SPACE ROOM BACKGROUND === */}

        {/* Upper wall - space window area */}
        <div className="office-wall-upper" aria-hidden="true" />

        {/* Space window */}
        <div className="office-window-v2" aria-hidden="true">
          {/* Deep space background */}
          <div className="office-window-bg" aria-hidden="true" />

          {/* Stars */}
          {stars.map((star, i) => (
            <span
              key={i}
              className="office-star-v2"
              style={{
                left: star.left,
                top: star.top,
                width: star.size,
                height: star.size,
                animationDelay: `${i * 0.3}s`,
              }}
            />
          ))}

          {/* Earth */}
          <div className="office-earth-v2" aria-hidden="true">
            {/* Continents */}
            <div className="earth-continent earth-continent-1" aria-hidden="true" />
            <div className="earth-continent earth-continent-2" aria-hidden="true" />
            <div className="earth-continent earth-continent-3" aria-hidden="true" />
            <div className="earth-continent earth-continent-4" aria-hidden="true" />
            <div className="earth-continent earth-continent-5" aria-hidden="true" />
            {/* Ice caps */}
            <div className="earth-ice earth-ice-north" aria-hidden="true" />
            <div className="earth-ice earth-ice-south" aria-hidden="true" />
            {/* Cloud swirls */}
            <div className="earth-cloud earth-cloud-1" aria-hidden="true" />
            <div className="earth-cloud earth-cloud-2" aria-hidden="true" />
            <div className="earth-cloud earth-cloud-3" aria-hidden="true" />
            <div className="earth-cloud earth-cloud-4" aria-hidden="true" />
            {/* Atmosphere rim */}
            <div className="earth-atmosphere" aria-hidden="true" />
          </div>

          {/* Nebula glow */}
          <div className="office-nebula office-nebula-1" aria-hidden="true" />
          <div className="office-nebula office-nebula-2" aria-hidden="true" />

          {/* Lunar surface */}
          <div className="office-lunar-surface" aria-hidden="true">
            {/* Craters */}
            <div className="lunar-crater lunar-crater-1" aria-hidden="true" />
            <div className="lunar-crater lunar-crater-2" aria-hidden="true" />
            <div className="lunar-crater lunar-crater-3" aria-hidden="true" />
            <div className="lunar-crater lunar-crater-4" aria-hidden="true" />
            <div className="lunar-crater lunar-crater-5" aria-hidden="true" />
            <div className="lunar-crater lunar-crater-6" aria-hidden="true" />
            {/* Distant structures */}
            <div className="lunar-structure lunar-structure-1" aria-hidden="true" />
            <div className="lunar-structure lunar-structure-2" aria-hidden="true" />
            <div className="lunar-structure lunar-structure-3" aria-hidden="true" />
          </div>
        </div>

        {/* Structural ribs on the wall */}
        {[10, 35, 60, 85].map((pct) => (
          <div key={`rib-${pct}`} className="office-wall-rib" style={{ left: `${pct}%` }} aria-hidden="true" />
        ))}

        {/* Ceiling lights */}
        {[8, 38, 68].map((pct) => (
          <div key={`light-${pct}`} className="office-ceiling-light" style={{ left: `${pct}%` }} aria-hidden="true">
            <div className="office-ceiling-light-glow" aria-hidden="true" />
          </div>
        ))}

        {/* Floor area */}
        <div className="office-floor-v2" aria-hidden="true" />
        <div className="office-floor-bottom" aria-hidden="true" />

        {/* Wall trim line */}
        <div className="office-wall-trim" aria-hidden="true" />
        <div className="office-wall-trim-highlight" aria-hidden="true" />

        {/* Floor lane markers */}
        <div className="office-floor-lane" aria-hidden="true" />

        {/* Ambient ceiling light glow on floor */}
        <div className="office-floor-glow office-floor-glow-1" aria-hidden="true" />
        <div className="office-floor-glow office-floor-glow-2" aria-hidden="true" />
        <div className="office-floor-glow office-floor-glow-3" aria-hidden="true" />

        {/* === SIDE WALL ITEMS === */}

        {/* Left wall: charts, whiteboard, water cooler */}
        <div className="office-chart office-chart-line" aria-hidden="true">
          <svg viewBox="0 0 40 20" fill="none" aria-hidden="true">
            <polyline points="0,18 8,12 16,15 24,6 32,9 40,3" stroke="#33ff66" strokeWidth="1.5" opacity="0.6" />
            <polyline points="0,16 8,14 16,10 24,12 32,5 40,8" stroke="#6699ff" strokeWidth="1" opacity="0.4" />
          </svg>
        </div>
        <div className="office-chart office-chart-bar" aria-hidden="true">
          <div className="office-bar-chart-bars">
            <div className="office-bar" style={{ height: "60%" }} />
            <div className="office-bar" style={{ height: "80%" }} />
            <div className="office-bar" style={{ height: "45%" }} />
            <div className="office-bar" style={{ height: "90%" }} />
            <div className="office-bar" style={{ height: "70%" }} />
          </div>
        </div>
        <div className="office-whiteboard" aria-hidden="true">
          <div className="office-whiteboard-line office-whiteboard-line-1" />
          <div className="office-whiteboard-line office-whiteboard-line-2" />
          <div className="office-whiteboard-line office-whiteboard-line-3" />
          <div className="office-whiteboard-line office-whiteboard-line-4" />
        </div>
        <img className="office-prop office-watercooler-v2" src="/assets/sprites/watercooler.png" alt="" aria-hidden="true" />

        {/* Right wall: charts, calendar */}
        <div className="office-chart office-chart-line-v2" aria-hidden="true">
          <svg viewBox="0 0 40 20" fill="none" aria-hidden="true">
            <polyline points="0,18 8,12 16,15 24,6 32,9 40,3" stroke="#33ff66" strokeWidth="1.5" opacity="0.6" />
            <polyline points="0,16 8,14 16,10 24,12 32,5 40,8" stroke="#6699ff" strokeWidth="1" opacity="0.4" />
          </svg>
        </div>
        <div className="office-chart office-chart-bar-v2" aria-hidden="true">
          <div className="office-bar-chart-bars">
            <div className="office-bar" style={{ height: "55%" }} />
            <div className="office-bar" style={{ height: "75%" }} />
            <div className="office-bar" style={{ height: "40%" }} />
            <div className="office-bar" style={{ height: "85%" }} />
          </div>
        </div>
        <div className="office-calendar" aria-hidden="true">
          <div className="office-calendar-header" />
          <div className="office-calendar-grid">
            {Array.from({ length: 15 }).map((_, i) => (
              <div key={i} className="office-calendar-day" />
            ))}
          </div>
        </div>

        {/* Floor props: plants */}
        <div className="office-plant" style={{ left: 240, top: 230 }} aria-hidden="true">
          <div className="office-plant-pot" />
          <div className="office-plant-leaf office-plant-leaf-1" />
          <div className="office-plant-leaf office-plant-leaf-2" />
          <div className="office-plant-leaf office-plant-leaf-3" />
        </div>
        <div className="office-plant" style={{ left: 470, top: 230 }} aria-hidden="true">
          <div className="office-plant-pot" />
          <div className="office-plant-leaf office-plant-leaf-1" />
          <div className="office-plant-leaf office-plant-leaf-2" />
          <div className="office-plant-leaf office-plant-leaf-3" />
        </div>
        <div className="office-plant" style={{ left: 690, top: 230 }} aria-hidden="true">
          <div className="office-plant-pot" />
          <div className="office-plant-leaf office-plant-leaf-1" />
          <div className="office-plant-leaf office-plant-leaf-2" />
          <div className="office-plant-leaf office-plant-leaf-3" />
        </div>
        <div className="office-plant" style={{ left: 1140, top: 225 }} aria-hidden="true">
          <div className="office-plant-pot" />
          <div className="office-plant-leaf office-plant-leaf-1" />
          <div className="office-plant-leaf office-plant-leaf-2" />
          <div className="office-plant-leaf office-plant-leaf-3" />
        </div>

        {/* Nameplate on supervisor desk */}
        <div className="office-nameplate" style={{ left: 960, top: 240 }} aria-hidden="true">
          <span>BOSS</span>
        </div>

        {/* Water pipe on reviewer desk */}
        <div className="office-water-pipe" style={{ left: 390, top: 245 }} aria-hidden="true">
          <div className="water-pipe-base">
            <div className="water-pipe-water" />
            <div className="water-pipe-highlight" />
          </div>
          <div className="water-pipe-neck">
            <div className="water-pipe-neck-highlight" />
          </div>
          <div className="water-pipe-mouth" />
          <div className="water-pipe-bowl">
            <div className="water-pipe-bowl-head" />
          </div>
          {/* Bubbles animation */}
          {!reducedMotion && (
            <>
              <div className="water-pipe-bubble water-pipe-bubble-1" />
              <div className="water-pipe-bubble water-pipe-bubble-2" />
            </>
          )}
        </div>

        {/* === DESKS WITH CHAIRS AND MONITORS === */}
        {desks.map((d, i) => {
          const agentRole = agents[i]?.role;
          const isActive = agentRole ? isAgentActive(agentRole) : false;
          return (
            <div key={`desk-${i}`} aria-hidden="true">
              {/* Desk */}
              <div className="office-desk" style={{ left: d.deskX, top: d.deskY, width: DESK_W, height: DESK_H }}>
                <div className="office-desk-top" />
                <div className="office-desk-leg office-desk-leg-left" />
                <div className="office-desk-leg office-desk-leg-right" />
                <div className="office-desk-edge" />
              </div>
              {/* Chair */}
              <div className="office-chair" style={{ left: d.chairX, top: d.chairY, width: 55, height: 60 }}>
                <div className="office-chair-back" />
                <div className="office-chair-seat" />
                <div className="office-chair-leg office-chair-leg-left" />
                <div className="office-chair-leg office-chair-leg-right" />
              </div>
              {/* Monitor */}
              <div className="office-monitor" style={{ left: d.monitorX, top: d.monitorY, width: 48, height: 48 }}>
                <div className="office-monitor-frame">
                  <div className="office-monitor-screen">
                    {!reducedMotion && (
                      <div className="office-monitor-code">
                        <div className="office-monitor-line office-monitor-line-1" />
                        <div className="office-monitor-line office-monitor-line-2" />
                        <div className="office-monitor-line office-monitor-line-3" />
                        <div className="office-monitor-line office-monitor-line-4" />
                        <div className="office-monitor-line office-monitor-line-5" />
                      </div>
                    )}
                  </div>
                </div>
                <div className="office-monitor-stand" />
              </div>
              {/* Mug */}
              <div className="office-mug" style={{ left: d.mugX, top: d.mugY, width: 40, height: 40 }}>
                <div className="office-mug-body">
                  <div className="office-mug-handle" />
                </div>
                {!reducedMotion && <div className="office-mug-steam" />}
              </div>
              {/* Active desk glow */}
              {isActive && !reducedMotion && (
                <div className="office-desk-glow" style={{ left: d.deskX - 6, top: d.deskY - 6, width: DESK_W + 12, height: DESK_H + 12 }} />
              )}
            </div>
          );
        })}

        {/* === PIXEL ART FURNITURE === */}

        {/* Ping pong table */}
        <img className="office-prop office-pingpong-v2" src="/assets/sprites/pingpong.png" alt="" aria-hidden="true" />
        {/* Ping pong ball - animated when active */}
        {pingPongActive && !reducedMotion && (
          <div className="office-pingpong-ball" aria-hidden="true" />
        )}

        {/* Hookah lounge */}
        <img className="office-prop office-cushion office-cushion-1" src="/assets/sprites/cushion.png" alt="" aria-hidden="true" />
        <img className="office-prop office-cushion office-cushion-2" src="/assets/sprites/cushion.png" alt="" aria-hidden="true" />
        <img className="office-prop office-cushion office-cushion-3" src="/assets/sprites/cushion.png" alt="" aria-hidden="true" />
        <img className="office-prop office-hookah-v2" src="/assets/sprites/hookah.png" alt="" aria-hidden="true" />
        {/* Hookah smoke */}
        {hookahActive && !reducedMotion && (
          <>
            <div className="office-hookah-smoke office-hookah-smoke-1" aria-hidden="true" />
            <div className="office-hookah-smoke office-hookah-smoke-2" aria-hidden="true" />
            <div className="office-hookah-smoke office-hookah-smoke-3" aria-hidden="true" />
            <div className="office-hookah-smoke office-hookah-smoke-4" aria-hidden="true" />
            <div className="office-hookah-smoke office-hookah-smoke-5" aria-hidden="true" />
          </>
        )}

        {/* TV + couch */}
        <img className="office-prop office-tv-v2" src="/assets/sprites/tv.png" alt="" aria-hidden="true" />
        <img className="office-prop office-couch-v2" src="/assets/sprites/couch.png" alt="" aria-hidden="true" />

        {/* === AGENT CHARACTERS === */}
        {agents.map((agent, index) => {
          const position = getAgentPosition(agent, currentStep);
          const isActive = activeAgents.has(agent.role);
          const isAwayFromHome = position.x !== agent.home.x || position.y !== agent.home.y;
          const spriteFrame = isActive && (running || isAwayFromHome) && !reducedMotion ? frame : 0;
          const speech = currentStep.office.speech[agent.role];
          const style = {
            "--agent-x": `${position.x / 12}%`,
            "--agent-y": `${position.y / 5.6}%`,
            "--agent-z": String(20 + index),
          } as CSSProperties;

          return (
            <div
              key={agent.role}
              className={`office-agent-v2${isActive ? " office-agent-v2-active" : ""}${
                isAwayFromHome ? " office-agent-v2-away" : ""
              }`}
              role="listitem"
              aria-label={`${agent.title} ${isActive ? "active" : "idle"}`}
              style={style}
            >
              {speech ? <div className="office-speech-v2">{speech}</div> : null}
              <div className="office-agent-shadow-v2" aria-hidden="true" />
              <div
                className="office-agent-sprite-v2"
                style={buildSpriteStyle(agent, position, spriteFrame)}
                aria-hidden="true"
              />
              {currentStep.office.carrier === agent.role ? (
                <div className="office-document-v2" aria-hidden="true" />
              ) : null}
              <div className="office-agent-label-v2">
                <strong>{agent.title}</strong>
                <span>{agent.name}</span>
              </div>
            </div>
          );
        })}

        {/* Sector label */}
        <div className="office-sector-label" aria-hidden="true">
          Mission Control
        </div>

        {/* Phase overlay */}
        <div className="office-phase-card-v2" aria-hidden="true">
          <span>AgroPredict AI</span>
          <strong>{currentStep.office.label}</strong>
        </div>

        {/* Ticker bar */}
        {!reducedMotion && (
          <div className="office-ticker" aria-hidden="true">
            <div className="office-ticker-text">
              {tickerText}{tickerText}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

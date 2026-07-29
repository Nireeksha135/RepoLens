import { getBezierPath, type EdgeProps } from "reactflow";
import type { EdgeType } from "../api/types";

// Signature element: edges are drawn as thin glowing "signal traces" with a
// small pulse animating along the path, like current moving through a
// circuit. This isn't decoration -- it's the literal thesis of the product
// (RepoLens visualizes how data flows through a codebase), so the one
// animated flourish on the page is spent reinforcing that idea rather than
// applied generically.

const STYLE_BY_EDGE_TYPE: Record<EdgeType, { dash?: string; opacity: number }> = {
  imports: { opacity: 0.55 },
  calls: { opacity: 0.85 },
  defines: { dash: "3 4", opacity: 0.4 },
};

export default function SignalEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<{ edgeType: EdgeType; highlighted?: boolean }>) {
  const [path] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeType = data?.edgeType ?? "imports";
  const style = STYLE_BY_EDGE_TYPE[edgeType];
  const highlighted = data?.highlighted;
  const stroke = highlighted ? "var(--signal)" : "var(--border-bright)";

  return (
    <>
      <path
        id={id}
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={highlighted ? 1.75 : 1.25}
        strokeDasharray={style.dash}
        opacity={highlighted ? 1 : style.opacity}
        style={{ transition: "stroke 150ms, opacity 150ms" }}
      />
      {edgeType !== "defines" && (
        <circle r={highlighted ? 3 : 2} fill={highlighted ? "var(--signal)" : "var(--node-component)"}>
          <animateMotion dur={highlighted ? "1.1s" : "2.6s"} repeatCount="indefinite" path={path} />
        </circle>
      )}
    </>
  );
}

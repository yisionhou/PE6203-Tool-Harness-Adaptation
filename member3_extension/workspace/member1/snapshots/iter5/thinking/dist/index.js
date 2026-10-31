#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { SequentialThinkingServer } from './lib.js';
const server = new McpServer({
    name: "sequential-thinking-server",
    version: "0.2.0",
});
const thinkingServer = new SequentialThinkingServer();
const parallelBranches = new Map();
server.registerTool("sequentialthinking", {
    title: "Sequential Thinking",
    description: `A detailed tool for dynamic and reflective problem-solving through sequential thoughts.
This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
Each thought can build on, question, or revise previous insights as understanding deepens.

When to use this tool:
- Breaking down complex problems into ordered steps
- Planning and design with room for revision along a single reasoning path
- Analysis that might need course correction within a linear progression
- Problems where the full scope might not be clear initially
- Problems that require a multi-step solution with maintained context
- Tasks that need to maintain context over multiple sequential steps
- Situations where irrelevant information needs to be filtered out
- When you need ONE coherent chain of reasoning rather than exploring multiple paths

For exploring multiple solution approaches simultaneously, use the parallel-thinking tool instead.
Once you have completed sequential or parallel thinking, use the convergent-synthesis tool to unify insights.

Key features:
- You can adjust total_thoughts up or down as you progress
- You can question or revise previous thoughts
- You can add more thoughts even after reaching what seemed like the end
- You can express uncertainty and explore alternative approaches
- Not every thought needs to build linearly - you can branch or backtrack
- Generates a solution hypothesis
- Verifies the hypothesis based on the Chain of Thought steps
- Repeats the process until satisfied
- Provides a correct answer

Parameters explained:
- thought: Your current thinking step, which can include:
  * Regular analytical steps
  * Revisions of previous thoughts
  * Questions about previous decisions
  * Realizations about needing more analysis
  * Changes in approach
  * Hypothesis generation
  * Hypothesis verification
- nextThoughtNeeded: True if you need more thinking, even if at what seemed like the end
- thoughtNumber: Current number in sequence (can go beyond initial total if needed)
- totalThoughts: Current estimate of thoughts needed (can be adjusted up/down)
- isRevision: A boolean indicating if this thought revises previous thinking
- revisesThought: If is_revision is true, which thought number is being reconsidered
- branchFromThought: If branching, which thought number is the branching point
- branchId: Identifier for the current branch (if any)
- needsMoreThoughts: If reaching end but realizing more thoughts needed

You should:
1. Start with an initial estimate of needed thoughts, but be ready to adjust
2. Feel free to question or revise previous thoughts
3. Don't hesitate to add more thoughts if needed, even at the "end"
4. Express uncertainty when present
5. Mark thoughts that revise previous thinking or branch into new paths
6. Ignore information that is irrelevant to the current step
7. Generate a solution hypothesis when appropriate
8. Verify the hypothesis based on the Chain of Thought steps
9. Repeat the process until satisfied with the solution
10. Provide a single, ideally correct answer as the final output
11. Only set nextThoughtNeeded to false when truly done and a satisfactory answer is reached
12. If multiple hypotheses or approaches were explored, consider using convergent-synthesis afterward`,
    inputSchema: {
        thought: z.string().describe("Your current thinking step"),
        nextThoughtNeeded: z.boolean().describe("Whether another thought step is needed"),
        thoughtNumber: z.number().int().min(1).describe("Current thought number (numeric value, e.g., 1, 2, 3)"),
        totalThoughts: z.number().int().min(1).describe("Estimated total thoughts needed (numeric value, e.g., 5, 10)"),
        isRevision: z.boolean().optional().describe("Whether this revises previous thinking"),
        revisesThought: z.number().int().min(1).optional().describe("Which thought is being reconsidered"),
        branchFromThought: z.number().int().min(1).optional().describe("Branching point thought number"),
        branchId: z.string().optional().describe("Branch identifier"),
        needsMoreThoughts: z.boolean().optional().describe("If more thoughts are needed"),
        thoughtPriority: z.enum(["critical", "high", "medium", "low"]).optional().describe("Priority level of this thought indicating its importance to the overall reasoning chain"),
        confidenceScore: z.number().min(0.0).max(1.0).optional().describe("Confidence level in this thought's validity, ranging from 0.0 (no confidence) to 1.0 (complete confidence)")
    },
    outputSchema: {
        thoughtNumber: z.number(),
        totalThoughts: z.number(),
        nextThoughtNeeded: z.boolean(),
        branches: z.array(z.string()),
        thoughtHistoryLength: z.number(),
        thoughtPriority: z.string().optional(),
        confidenceScore: z.number().optional(),
        averageConfidence: z.number().optional()
    },
}, async (args) => {
    const result = thinkingServer.processThought(args);
    if (result.isError) {
        return result;
    }
    // Parse the JSON response to get structured content
    const parsedContent = JSON.parse(result.content[0].text);
    
    // Enhance with priority and confidence tracking
    if (args.thoughtPriority) {
        parsedContent.thoughtPriority = args.thoughtPriority;
    }
    if (args.confidenceScore !== undefined) {
        parsedContent.confidenceScore = args.confidenceScore;
    }
    
    // Calculate average confidence if available
    const thoughtHistory = thinkingServer.getThoughtHistory();
    if (thoughtHistory && thoughtHistory.length > 0) {
        const confidenceScores = thoughtHistory
            .map(t => t.confidenceScore)
            .filter(c => c !== undefined && c !== null);
        if (confidenceScores.length > 0) {
            const avgConfidence = confidenceScores.reduce((sum, c) => sum + c, 0) / confidenceScores.length;
            parsedContent.averageConfidence = Math.round(avgConfidence * 100) / 100;
        }
    }
    
    return {
        content: [{
            type: "text",
            text: JSON.stringify(parsedContent, null, 2)
        }],
        structuredContent: parsedContent
    };
});
async function runServer() {
server.registerTool("convergent-synthesis", {
    title: "Convergent Synthesis",
    description: `A tool for synthesizing and unifying insights from multiple reasoning paths or extended thought chains.
This tool helps consolidate findings from sequential-thinking or parallel-thinking sessions into a coherent,
well-justified final answer by identifying common themes, resolving contradictions, and weighing evidence.

When to use this tool:
- After completing multiple parallel-thinking paths that need unification
- When sequential-thinking produced multiple hypotheses requiring integration
- To resolve contradictions between different reasoning approaches
- When you need to weigh evidence from diverse analytical paths
- To produce a final, consolidated answer from exploratory thinking
- When multiple valid perspectives need to be balanced into one conclusion

Key features:
- Aggregates insights from multiple thinking sessions
- Identifies convergence points and contradictions
- Weighs evidence strength across different reasoning paths
- Resolves conflicts through logical prioritization
- Produces a unified, well-justified final answer
- Maintains traceability to source reasoning paths

Parameters explained:
- synthesisId: Unique identifier for this synthesis session
- sourcePaths: Array of path/thought chain identifiers being synthesized (e.g., ["sequential_chain_1", "path_a", "path_b"])
- convergencePoints: Key insights or conclusions that multiple paths agree on
- contradictions: Points where reasoning paths conflict or disagree
- evidenceWeighting: Assessment of which paths provide stronger evidence (e.g., {"path_a": "strong", "path_b": "moderate"})
- resolutionStrategy: How contradictions are being resolved ("evidence_based", "logical_priority", "contextual_fit")
- synthesizedConclusion: The unified final answer or conclusion
- confidenceLevel: Confidence in the synthesized conclusion ("high", "moderate", "low")
- traceability: Mapping of conclusion elements back to source paths
- openQuestions: Any remaining uncertainties or areas needing further exploration

You should:
1. Clearly identify all source reasoning paths being synthesized
2. Extract and list convergence points where paths agree
3. Identify and document contradictions between paths
4. Assess the strength of evidence from each path
5. Apply a clear resolution strategy for conflicts
6. Produce a synthesized conclusion that integrates the best insights
7. Indicate confidence level based on evidence consistency
8. Maintain traceability so the conclusion can be audited
9. Note any open questions that synthesis could not resolve`,
    inputSchema: {
        synthesisId: z.string().describe("Unique identifier for this synthesis session"),
        sourcePaths: z.array(z.string()).describe("Array of path/chain identifiers being synthesized"),
        convergencePoints: z.array(z.string()).describe("Key insights where multiple paths agree"),
        contradictions: z.array(z.object({
            point: z.string(),
            conflictingPaths: z.array(z.string())
        })).optional().describe("Points where reasoning paths conflict"),
        evidenceWeighting: z.record(z.string(), z.enum(["strong", "moderate", "weak"])).describe("Assessment of evidence strength per path"),
        resolutionStrategy: z.enum(["evidence_based", "logical_priority", "contextual_fit", "consensus"]).describe("How contradictions are resolved"),
        synthesizedConclusion: z.string().describe("The unified final answer or conclusion"),
        confidenceLevel: z.enum(["high", "moderate", "low"]).describe("Confidence in the synthesized conclusion"),
        traceability: z.record(z.string(), z.array(z.string())).optional().describe("Mapping of conclusion elements to source paths"),
        openQuestions: z.array(z.string()).optional().describe("Remaining uncertainties or areas needing exploration")
    },
    outputSchema: {
        synthesisId: z.string(),
        sourcePathCount: z.number(),
        convergencePointCount: z.number(),
        contradictionCount: z.number(),
        resolutionStrategy: z.string(),
        confidenceLevel: z.string(),
        synthesizedConclusion: z.string(),
        openQuestionCount: z.number()
    },
}, async (args) => {
    const synthesisData = {
        synthesisId: args.synthesisId,
        sourcePaths: args.sourcePaths,
        convergencePoints: args.convergencePoints,
        contradictions: args.contradictions || [],
        evidenceWeighting: args.evidenceWeighting,
        resolutionStrategy: args.resolutionStrategy,
        synthesizedConclusion: args.synthesizedConclusion,
        confidenceLevel: args.confidenceLevel,
        traceability: args.traceability || {},
        openQuestions: args.openQuestions || [],
        timestamp: Date.now()
    };
    
    const result = {
        synthesisId: args.synthesisId,
        sourcePathCount: args.sourcePaths.length,
        convergencePointCount: args.convergencePoints.length,
        contradictionCount: (args.contradictions || []).length,
        resolutionStrategy: args.resolutionStrategy,
        confidenceLevel: args.confidenceLevel,
        synthesizedConclusion: args.synthesizedConclusion,
        openQuestionCount: (args.openQuestions || []).length,
        synthesisData: synthesisData
    };
    
    return {
        content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
        }],
        structuredContent: result
    };
});


server.registerTool("parallel-thinking", {
    title: "Parallel Thinking",
    description: `A tool for exploring multiple solution paths or perspectives simultaneously.
This tool enables concurrent analysis of different approaches, allowing you to evaluate
multiple hypotheses, strategies, or viewpoints before converging on a solution.

When to use this tool:
- Exploring multiple solution strategies simultaneously
- Comparing different approaches or perspectives
- Brainstorming where diverse ideas should be developed in parallel
- Problems with multiple valid solution paths
- Decision-making that requires evaluating trade-offs between options
- Creative problem-solving that benefits from divergent thinking
- Situations where you want to avoid premature commitment to one approach

Key features:
- Maintain multiple independent reasoning paths
- Each path can have its own chain of thoughts
- Paths can be compared, merged, or eliminated
- Supports convergence when paths lead to similar conclusions
- Allows switching between paths or creating new ones
- Final synthesis combines insights from all paths

Parameters explained:
- pathId: Identifier for the current reasoning path (e.g., "approach_a", "strategy_1")
- thought: Current thinking step within this path
- pathNumber: Current path number in sequence
- totalPaths: Total number of paths being explored
- thoughtInPath: Which thought number within this specific path
- pathStatus: Status of this path ("active", "completed", "abandoned", "merged")
- relatedPaths: Other path IDs that relate to or conflict with this one
- convergenceDetected: Whether this path is converging with others
- needsNewPath: Whether a new parallel path should be created
- readyForSynthesis: Whether all paths are ready to be synthesized into a final answer

You should:
1. Start by identifying distinct approaches or perspectives to explore
2. Develop each path independently with its own reasoning chain
3. Note when paths converge or conflict
4. Abandon paths that prove unproductive
5. Create new paths if promising directions emerge
6. Mark readyForSynthesis as true when paths are adequately explored
7. Use the convergent-synthesis tool to unify insights from all viable paths into a final solution`,
    inputSchema: {
        pathId: z.string().describe("Identifier for the current reasoning path"),
        thought: z.string().describe("Current thinking step within this path"),
        pathNumber: z.number().int().min(1).describe("Current path number"),
        totalPaths: z.number().int().min(1).describe("Total number of paths being explored"),
        thoughtInPath: z.number().int().min(1).describe("Thought number within this specific path"),
        pathStatus: z.enum(["active", "completed", "abandoned", "merged"]).describe("Status of this path"),
        relatedPaths: z.array(z.string()).optional().describe("Related or conflicting path IDs"),
        convergenceDetected: z.boolean().optional().describe("Whether converging with other paths"),
        needsNewPath: z.boolean().optional().describe("Whether to create a new parallel path"),
        readyForSynthesis: z.boolean().describe("Whether ready to synthesize all paths")
    },
    outputSchema: {
        pathId: z.string(),
        pathNumber: z.number(),
        totalPaths: z.number(),
        thoughtInPath: z.number(),
        pathStatus: z.string(),
        activePaths: z.array(z.string()),
        convergencePoints: z.array(z.string())
    },
}, async (args) => {
    const pathKey = args.pathId;
    
    if (!parallelBranches.has(pathKey)) {
        parallelBranches.set(pathKey, {
            thoughts: [],
            status: args.pathStatus,
            createdAt: Date.now()
        });
    }
    
    const pathData = parallelBranches.get(pathKey);
    pathData.thoughts.push({
        thought: args.thought,
        thoughtNumber: args.thoughtInPath,
        timestamp: Date.now()
    });
    pathData.status = args.pathStatus;
    
    if (args.pathStatus === "abandoned" || args.pathStatus === "merged") {
        pathData.completedAt = Date.now();
    }
    
    const activePaths = Array.from(parallelBranches.entries())
        .filter(([_, data]) => data.status === "active")
        .map(([id, _]) => id);
    
    const convergencePoints = args.relatedPaths || [];
    
    const result = {
        pathId: args.pathId,
        pathNumber: args.pathNumber,
        totalPaths: args.totalPaths,
        thoughtInPath: args.thoughtInPath,
        pathStatus: args.pathStatus,
        activePaths: activePaths,
        convergencePoints: convergencePoints
    };
    
    if (args.readyForSynthesis) {
        const allPaths = Array.from(parallelBranches.entries()).map(([id, data]) => ({
            pathId: id,
            thoughtCount: data.thoughts.length,
            status: data.status
        }));
        result.synthesisReady = true;
        result.pathsSummary = allPaths;
    }
    
    return {
        content: [{
            type: "text",
            text: JSON.stringify(result, null, 2)
        }],
        structuredContent: result
    };
});
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error("Sequential Thinking MCP Server running on stdio");
}
runServer().catch((error) => {
    console.error("Fatal error running server:", error);
    process.exit(1);
});
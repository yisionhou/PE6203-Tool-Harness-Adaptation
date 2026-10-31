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
11. Only set nextThoughtNeeded to false when truly done and a satisfactory answer is reached`,
    inputSchema: {
        thought: z.string().describe("Your current thinking step"),
        nextThoughtNeeded: z.boolean().describe("Whether another thought step is needed"),
        thoughtNumber: z.number().int().min(1).describe("Current thought number (numeric value, e.g., 1, 2, 3)"),
        totalThoughts: z.number().int().min(1).describe("Estimated total thoughts needed (numeric value, e.g., 5, 10)"),
        isRevision: z.boolean().optional().describe("Whether this revises previous thinking"),
        revisesThought: z.number().int().min(1).optional().describe("Which thought is being reconsidered"),
        branchFromThought: z.number().int().min(1).optional().describe("Branching point thought number"),
        branchId: z.string().optional().describe("Branch identifier"),
        needsMoreThoughts: z.boolean().optional().describe("If more thoughts are needed")
    },
    outputSchema: {
        thoughtNumber: z.number(),
        totalThoughts: z.number(),
        nextThoughtNeeded: z.boolean(),
        branches: z.array(z.string()),
        thoughtHistoryLength: z.number()
    },
}, async (args) => {
    const result = thinkingServer.processThought(args);
    if (result.isError) {
        return result;
    }
    // Parse the JSON response to get structured content
    const parsedContent = JSON.parse(result.content[0].text);
    return {
        content: result.content,
        structuredContent: parsedContent
    };
});
async function runServer() {
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
6. Synthesize insights from all viable paths into a final solution
7. Only set readyForSynthesis to true when all paths have been adequately explored`,
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
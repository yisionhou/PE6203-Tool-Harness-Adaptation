#!/usr/bin/env node
import express from "express";
import cors from "cors";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import { z } from "zod";
/**
 * YGOCDB API 参考:
 * - https://ygocdb.com/api/v0/?search=
 *
 * 图片API:
 * - https://cdn.233.momobako.com/ygopro/pics/<id>.jpg
 *
 * 服务端提供以下工具:
 * 1) search_cards - 通过关键字搜索卡牌
 * 2) get_card_by_id - 通过卡牌ID获取单张卡牌
 * 3) get_card_image - 通过卡牌ID获取卡牌图片
 */
// Express应用和端口配置
const app = express();
const PORT = process.env.PORT || 8081;
// CORS配置，适用于基于浏览器的MCP客户端
app.use(cors({
    origin: '*', // 生产环境中请适当配置
    exposedHeaders: ['Mcp-Session-Id', 'mcp-protocol-version'],
    allowedHeaders: ['Content-Type', 'mcp-session-id'],
}));
app.use(express.json());
// 定义基础URL
const BASE_URL = "https://ygocdb.com/api/v0";
// 配置模式（可选 - 如果不需要配置可以跳过）
export const configSchema = z.object({
    // 目前YGOCDB API不需要特殊配置，但保留扩展性
    apiUrl: z.string().optional().default(BASE_URL).describe("YGOCDB API基础URL"),
    timeout: z.number().optional().default(10000).describe("请求超时时间（毫秒）"),
});
// 从查询参数解析配置
function parseConfig(req) {
    const configParam = req.query.config;
    if (configParam) {
        try {
            return JSON.parse(Buffer.from(configParam, 'base64').toString());
        }
        catch {
            return {};
        }
    }
    return {};
}
// 搜索卡牌工具
const SEARCH_CARDS_TOOL = {
    name: "search_cards",
    description: "通过关键字搜索游戏王卡牌，可以搜索卡牌名称、效果文本等。",
    inputSchema: {
        type: "object",
        properties: {
            query: {
                type: "string",
                description: "搜索关键字，可以是卡牌名称、效果描述等"
            },
            limit: {
                type: "number",
                description: "可选，限制返回结果数量，默认返回全部结果"
            },
            exact: {
                type: "boolean",
                description: "可选，是否仅保留与关键字完全匹配的卡名结果，默认 false"
            }
        },
        required: ["query"]
    },
    annotations: {
        title: "通过关键字搜索游戏王卡牌",
        readOnlyHint: true,
        openWorldHint: true
    }
};
// 通过ID获取卡牌工具
const GET_CARD_BY_ID_TOOL = {
    name: "get_card_by_id",
    description: "通过卡牌ID获取单张游戏王卡牌的详细信息",
    inputSchema: {
        type: "object",
        properties: {
            id: {
                type: "string",
                description: "游戏王卡牌ID，通常为八位数字"
            }
        },
        required: ["id"]
    },
    annotations: {
        title: "通过ID获取单张游戏王卡牌",
        readOnlyHint: true,
        openWorldHint: true
    }
};
// 获取卡牌图片工具
const GET_CARD_IMAGE_TOOL = {
    name: "get_card_image",
    description: "通过卡牌ID获取游戏王卡牌的图片",
    inputSchema: {
        type: "object",
        properties: {
            id: {
                type: "string",
                description: "游戏王卡牌ID，可以使用search_cards工具搜索"
            }
        },
        required: ["id"]
    },
    annotations: {
        title: "通过ID获取游戏王卡牌图片",
        readOnlyHint: true,
        openWorldHint: true
    }
};
// 返回我们的工具集
const YGOCDB_TOOLS = [
    SEARCH_CARDS_TOOL,
    GET_CARD_BY_ID_TOOL,
    GET_CARD_IMAGE_TOOL
];
// 处理响应的通用函数
async function handleYgocdbResponse(response) {
    if (!response.ok) {
        // 尝试解析错误
        let errorObj = null;
        try {
            errorObj = await response.json();
        }
        catch {
            // 回退到通用错误
        }
        if (errorObj && errorObj.message) {
            return {
                content: [
                    {
                        type: "text",
                        text: `YGOCDB API 错误: ${errorObj.message} (状态码: ${response.status})`
                    }
                ],
                isError: true
            };
        }
        else {
            return {
                content: [
                    {
                        type: "text",
                        text: `HTTP 错误 ${response.status}: ${response.statusText}`
                    }
                ],
                isError: true
            };
        }
    }
    // 如果正常，解析 JSON
    const data = await response.json();
    return {
        content: [
            {
                type: "text",
                text: JSON.stringify(data, null, 2)
            }
        ],
        isError: false
    };
}
// 搜索卡牌处理函数
async function handleSearchCards(query, config, options = {}) {
    const url = `${config?.apiUrl || BASE_URL}/?search=${encodeURIComponent(query)}`;
    const response = await fetch(url);
    if (!response.ok) {
        return handleYgocdbResponse(response);
    }
    let data = await response.json();
    if (Array.isArray(data)) {
        if (options.exact === true) {
            data = data.filter((card) => {
                const name = typeof card?.cn_name === "string"
                    ? card.cn_name
                    : typeof card?.name === "string"
                        ? card.name
                        : "";
                return name === query;
            });
        }
        if (typeof options.limit === "number" && Number.isFinite(options.limit) && options.limit > 0) {
            data = data.slice(0, Math.floor(options.limit));
        }
    }
    return {
        content: [
            {
                type: "text",
                text: JSON.stringify(data, null, 2)
            }
        ],
        isError: false
    };
}
// 通过ID获取卡牌处理函数
async function handleGetCardById(id, config) {
    const url = `${config?.apiUrl || BASE_URL}/?search=${encodeURIComponent(id)}`;
    const response = await fetch(url);
    return handleYgocdbResponse(response);
}
// 通过ID获取卡牌图片处理函数
async function handleGetCardImage(id, config) {
    const url = `https://cdn.233.momobako.com/ygopro/pics/${encodeURIComponent(id)}.jpg`;
    try {
        const response = await fetch(url);
        // 处理错误响应
        if (!response.ok) {
            return {
                content: [
                    {
                        type: "text",
                        text: `获取卡牌图片失败: HTTP 错误 ${response.status}: ${response.statusText}`
                    }
                ],
                isError: true
            };
        }
        // 处理成功响应 - 读取图片数据
        const buffer = await response.arrayBuffer();
        const base64Data = Buffer.from(buffer).toString('base64');
        const contentType = response.headers.get('content-type') || 'image/jpeg';
        // 返回图像内容
        return {
            content: [
                {
                    type: "text",
                    text: `卡牌图片 (ID: ${id})`
                },
                {
                    type: "image",
                    data: base64Data,
                    mimeType: contentType
                }
            ],
            isError: false
        };
    }
    catch (error) {
        // 捕获所有其他错误（网络错误、解析错误等）
        return {
            content: [
                {
                    type: "text",
                    text: `获取卡牌图片失败: ${error.message}`
                }
            ],
            isError: true
        };
    }
}
// 创建MCP服务器和注册工具
export default function createServer({ config, }) {
    const server = new Server({
        name: "mcp-server/ygocdb",
        version: "1.1.0"
    }, {
        capabilities: {
            tools: {}
        }
    });
    // 设置工具列表处理器
    server.setRequestHandler(ListToolsRequestSchema, async () => ({
        tools: YGOCDB_TOOLS
    }));
    // 设置工具调用处理器
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
        try {
            const { name, arguments: args } = request.params;
            switch (name) {
                case "search_cards": {
                    const { query, limit, exact } = args;
                    return await handleSearchCards(query, config, { limit, exact });
                }
                case "get_card_by_id": {
                    const { id } = args;
                    return await handleGetCardById(id, config);
                }
                case "get_card_image": {
                    const { id } = args;
                    return await handleGetCardImage(id, config);
                }
                default:
                    return {
                        content: [
                            {
                                type: "text",
                                text: `错误: 未知的工具名称 "${name}"`
                            }
                        ],
                        isError: true
                    };
            }
        }
        catch (err) {
            return {
                content: [
                    {
                        type: "text",
                        text: `错误: ${err.message}`
                    }
                ],
                isError: true
            };
        }
    });
    return server;
}
// 处理MCP请求的端点
app.all('/mcp', async (req, res) => {
    try {
        // 解析配置（可选）
        const rawConfig = parseConfig(req);
        // 验证和解析配置
        const config = configSchema.parse({
            apiUrl: rawConfig.apiUrl || process.env.YGOCDB_API_URL || BASE_URL,
            timeout: rawConfig.timeout || parseInt(process.env.YGOCDB_TIMEOUT || "10000"),
        });
        const server = createServer({ config });
        const transport = new StreamableHTTPServerTransport({
            sessionIdGenerator: undefined,
        });
        // 请求关闭时清理
        res.on('close', () => {
            transport.close();
            server.close();
        });
        await server.connect(transport);
        await transport.handleRequest(req, res, req.body);
    }
    catch (error) {
        console.error('处理MCP请求时出错:', error);
        if (!res.headersSent) {
            res.status(500).json({
                jsonrpc: '2.0',
                error: { code: -32603, message: '内部服务器错误' },
                id: null,
            });
        }
    }
});
// 主函数以适当模式启动服务器
async function main() {
    const transport = process.env.TRANSPORT || 'stdio';
    if (transport === 'http') {
        // 在HTTP模式下运行
        app.listen(PORT, () => {
            console.log(`YGOCDB MCP HTTP服务器监听端口 ${PORT}`);
        });
    }
    else {
        // 可选：如果需要向后兼容，添加stdio传输
        const config = configSchema.parse({
            apiUrl: process.env.YGOCDB_API_URL || BASE_URL,
            timeout: parseInt(process.env.YGOCDB_TIMEOUT || "10000"),
        });
        // 使用配置创建服务器
        const server = createServer({ config });
        // 开始在stdin上接收消息并在stdout上发送消息
        const stdioTransport = new StdioServerTransport();
        await server.connect(stdioTransport);
        console.error("YGOCDB MCP服务器在stdio模式下运行");
    }
}
// 启动服务器
main().catch((error) => {
    console.error("服务器错误:", error);
    process.exit(1);
});
//# sourceMappingURL=index.js.map
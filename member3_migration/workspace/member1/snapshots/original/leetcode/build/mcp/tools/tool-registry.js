import { RegistryBase } from "../../common/registry-base.js";
/**
 * Base registry class for LeetCode tools that provides site type detection and authentication status checks.
 * This abstract class defines the framework for registering different categories of tools based on
 * site version (Global or CN) and authentication requirements.
 */
export class ToolRegistry extends RegistryBase {
    server;
    leetcodeService;
    /**
     * Creates a new tool registry instance.
     *
     * @param server - The MCP server instance to register tools with
     * @param leetcodeService - The LeetCode service implementation to use for API calls
     */
    constructor(server, leetcodeService) {
        super(server, leetcodeService);
        this.server = server;
        this.leetcodeService = leetcodeService;
    }
    /**
     * Registers all applicable tools based on site version and authentication status.
     * This method follows a specific registration sequence to ensure proper tool organization.
     */
    registerTools() {
        this.register();
    }
}
//# sourceMappingURL=tool-registry.js.map
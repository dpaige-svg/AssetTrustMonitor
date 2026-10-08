local fs = require("@lune/fs")
local process = require("@lune/process")
local roblox = require("@lune/roblox")

local PROCESSING_PATH = "../processing/Processing_rbxm"
local DESTINATION_PATH = "src/Workspace"
local MAX_INSTANCES = 20000
local MAX_DEPTH = 128
local MAX_PARTS = 10000

local file = process.args[1]
if file == nil or file == "" or file:find("[/\\]") then
    print("A single safe asset filename is required")
    process.exit(2)
end
if not (file:match("%.rbxm$") or file:match("%.rbxmx$")) then
    print("Unsupported model extension: " .. file)
    process.exit(2)
end

local filePath = PROCESSING_PATH .. "/" .. file
if not fs.isFile(filePath) then
    print("Processing file is missing: " .. file)
    process.exit(2)
end

local success, result = pcall(function()
    local rbxmData = fs.readFile(filePath)
    local instances = roblox.deserializeModel(rbxmData)
    if #instances == 0 then
        error("Model contains no root instances")
    end

    local instanceCount = 0
    local partCount = 0
    local disabledScriptCount = 0
    local stack = {}
    for _, rootInstance in ipairs(instances) do
        table.insert(stack, { instance = rootInstance, depth = 1 })
    end

    while #stack > 0 do
        local entry = table.remove(stack)
        local instance = entry.instance
        local depth = entry.depth
        instanceCount += 1

        if instanceCount > MAX_INSTANCES then
            error("Model exceeds safe instance limit (" .. tostring(MAX_INSTANCES) .. ")")
        end
        if depth > MAX_DEPTH then
            error("Model exceeds safe hierarchy depth (" .. tostring(MAX_DEPTH) .. ")")
        end

        if instance:IsA("Script") or instance:IsA("LocalScript") then
            local disabled = pcall(function()
                instance.Disabled = true
            end)
            if disabled then
                disabledScriptCount += 1
            end
        end

        if instance:IsA("BasePart") then
            partCount += 1
            if partCount > MAX_PARTS then
                error("Model exceeds safe part limit (" .. tostring(MAX_PARTS) .. ")")
            end
            pcall(function()
                instance.Anchored = true
            end)
        end

        for _, child in ipairs(instance:GetChildren()) do
            table.insert(stack, { instance = child, depth = depth + 1 })
        end
    end

    local folderName = file:match("(.+)%.rbxm$") or file:match("(.+)%.rbxmx$") or file
    local wrapperFolder = roblox.Instance.new("Folder")
    wrapperFolder.Name = folderName
    for _, instance in ipairs(instances) do
        instance.Parent = wrapperFolder
    end

    local wrappedData = roblox.serializeModel({ wrapperFolder })
    if not fs.isDir(DESTINATION_PATH) then
        fs.writeDir(DESTINATION_PATH)
    end

    local destinationPath = DESTINATION_PATH .. "/" .. file
    fs.writeFile(filePath, wrappedData)
    fs.move(filePath, destinationPath, true)

    return string.format(
        "Imported %s safely: %d instances, %d parts, %d scripts disabled",
        folderName,
        instanceCount,
        partCount,
        disabledScriptCount
    )
end)

if not success then
    print("Automatic import rejected for " .. file .. ": " .. tostring(result))
    print("Original retained in Assets for manual review")
    process.exit(1)
end

print(result)

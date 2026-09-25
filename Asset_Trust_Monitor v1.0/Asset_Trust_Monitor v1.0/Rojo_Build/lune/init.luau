local fs = require("@lune/fs")
local roblox = require("@lune/roblox")

local PROCESSING_PATH = "../processing/Processing_rbxm"
local DESTINATION_PATH = "src/Workspace"

local files = fs.readDir(PROCESSING_PATH)
local processedCount = 0

for _, file in ipairs(files) do
    if file:match("%.rbxm$") then
        local filePath = PROCESSING_PATH .. "/" .. file
        local rbxmData = fs.readFile(filePath)
        local instances = roblox.deserializeModel(rbxmData)
        local folderName = file:match("(.+)%.rbxm$") or file
        local wrapperFolder = roblox.Instance.new("Folder")
        wrapperFolder.Name = folderName
        if #instances > 0 then

            for _, instance in ipairs(instances) do
                instance.Parent = wrapperFolder
            end

            local wrappedData = roblox.serializeModel({wrapperFolder})
            fs.writeFile(filePath, wrappedData)

            -- Move to destination folder
            local destinationPath = DESTINATION_PATH .. "/" .. file
            -- Ensure destination directory exists
            if not fs.isDir(DESTINATION_PATH) then
                fs.writeDir(DESTINATION_PATH)
            end
            fs.move(filePath, destinationPath)

            print("Wrapped and moved:", folderName)
            processedCount = processedCount + 1

        end
    end
end

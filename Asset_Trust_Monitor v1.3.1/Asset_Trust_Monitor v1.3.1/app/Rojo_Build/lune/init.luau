local fs = require("@lune/fs")
local roblox = require("@lune/roblox")

local PROCESSING_PATH = "../processing/Processing_rbxm"
local DESTINATION_PATH = "src/Workspace"

local files = fs.readDir(PROCESSING_PATH)
local processedCount = 0

for _, file in ipairs(files) do
    if file:match("%.rbxm$") then
        local filePath = PROCESSING_PATH .. "/" .. file
        
        if fs.isFile(filePath) then
            -- Wrap processing in pcall to handle corrupted assets without crashing
            local success, err = pcall(function()

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
                    

                    -- ...existing code...


                    fs.move(filePath, destinationPath)

                    print("Wrapped and moved:", folderName)
                    processedCount = processedCount + 1
                end
            end)

            if not success then
                -- Clean error message for known issues
                local errorMsg = tostring(err)
                print("Warning: Failed to process " .. file)
                print(errorMsg)
                
                -- Fallback: Move the raw file to destination without wrapping
                -- This allows the file to "go through" even if Lune can't read it
                print("Attempting fallback: Moving raw file to Workspace...")
                
                local destinationPath = DESTINATION_PATH .. "/" .. file
                
                -- Ensure destination directory exists
                if not fs.isDir(DESTINATION_PATH) then
                    fs.writeDir(DESTINATION_PATH)
                end

                -- Remove existing file if it exists to allow overwrite
                -- ...existing code...

                -- Try to move the original file
                local moveSuccess, moveErr = pcall(function()
                    fs.move(filePath, destinationPath)
                end)
                
                if moveSuccess then
                    print("Fallback successful: Moved raw file to " .. destinationPath)
                    processedCount = processedCount + 1
                else
                    print("Fallback failed: " .. tostring(moveErr))
                end
            end
        end
    end
end

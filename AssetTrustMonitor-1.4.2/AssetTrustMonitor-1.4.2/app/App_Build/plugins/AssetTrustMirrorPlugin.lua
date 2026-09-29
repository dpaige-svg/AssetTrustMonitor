-- Asset Trust Mirror Plugin
-- Reads app-written signal data from Rojo-synced Shared module and verifies insertion in Studio.

local TOOLBAR_NAME = "Asset Trust"
local BUTTON_NAME = "Mirror"
local WIDGET_ID = "AssetTrustMirrorWidget"
local WIDGET_TITLE = "Asset Trust Mirror"

local toolbar = plugin:CreateToolbar(TOOLBAR_NAME)
local openButton = toolbar:CreateButton(BUTTON_NAME, "Open Asset Trust mirror panel", "")
openButton.ClickableWhenViewportHidden = true

local widgetInfo = DockWidgetPluginGuiInfo.new(
	Enum.InitialDockState.Right,
	true,
	false,
	320,
	182,
	260,
	150
)

local widget = plugin:CreateDockWidgetPluginGui(WIDGET_ID, widgetInfo)
widget.Title = WIDGET_TITLE
widget.Enabled = true

local root = Instance.new("Frame")
root.Size = UDim2.fromScale(1, 1)
root.BackgroundColor3 = Color3.fromRGB(30, 30, 30)
root.BorderSizePixel = 0
root.Parent = widget

local pad = Instance.new("UIPadding")
pad.PaddingTop = UDim.new(0, 12)
pad.PaddingBottom = UDim.new(0, 12)
pad.PaddingLeft = UDim.new(0, 12)
pad.PaddingRight = UDim.new(0, 12)
pad.Parent = root

local list = Instance.new("UIListLayout")
list.Padding = UDim.new(0, 8)
list.FillDirection = Enum.FillDirection.Vertical
list.HorizontalAlignment = Enum.HorizontalAlignment.Left
list.VerticalAlignment = Enum.VerticalAlignment.Top
list.Parent = root

local assetRow = Instance.new("Frame")
assetRow.Size = UDim2.new(1, 0, 0, 24)
assetRow.BackgroundColor3 = Color3.fromRGB(20, 20, 20)
assetRow.BorderSizePixel = 0
assetRow.Parent = root

local assetTitle = Instance.new("TextLabel")
assetTitle.Size = UDim2.new(0, 88, 1, 0)
assetTitle.BackgroundTransparency = 1
assetTitle.Font = Enum.Font.GothamBold
assetTitle.TextSize = 11
assetTitle.TextXAlignment = Enum.TextXAlignment.Left
assetTitle.TextYAlignment = Enum.TextYAlignment.Center
assetTitle.TextColor3 = Color3.fromRGB(240, 240, 240)
assetTitle.Text = "Current Asset:"
assetTitle.Parent = assetRow

local currentAsset = Instance.new("TextLabel")
currentAsset.Position = UDim2.new(0, 90, 0, 0)
currentAsset.Size = UDim2.new(1, -90, 1, 0)
currentAsset.BackgroundTransparency = 1
currentAsset.Font = Enum.Font.Code
currentAsset.TextWrapped = false
currentAsset.TextTruncate = Enum.TextTruncate.AtEnd
currentAsset.TextSize = 11
currentAsset.TextXAlignment = Enum.TextXAlignment.Left
currentAsset.TextYAlignment = Enum.TextYAlignment.Center
currentAsset.TextColor3 = Color3.fromRGB(230, 230, 230)
currentAsset.Text = "Waiting for asset..."
currentAsset.Parent = assetRow

local actionRow = Instance.new("Frame")
actionRow.Size = UDim2.new(1, 0, 0, 24)
actionRow.BackgroundTransparency = 1
actionRow.Parent = root

local actionLayout = Instance.new("UIListLayout")
actionLayout.FillDirection = Enum.FillDirection.Horizontal
actionLayout.HorizontalAlignment = Enum.HorizontalAlignment.Left
actionLayout.VerticalAlignment = Enum.VerticalAlignment.Center
actionLayout.Padding = UDim.new(0, 8)
actionLayout.Parent = actionRow

local copyRegexButton = Instance.new("TextButton")
copyRegexButton.Size = UDim2.new(0, 80, 1, 0)
copyRegexButton.BackgroundColor3 = Color3.fromRGB(45, 45, 45)
copyRegexButton.BorderSizePixel = 0
copyRegexButton.TextColor3 = Color3.fromRGB(235, 235, 235)
copyRegexButton.Font = Enum.Font.Gotham
copyRegexButton.TextSize = 11
copyRegexButton.Text = "Copy Regex"
copyRegexButton.Parent = actionRow

local flagAssetButton = Instance.new("TextButton")
flagAssetButton.Size = UDim2.new(0, 80, 1, 0)
flagAssetButton.BackgroundColor3 = Color3.fromRGB(45, 45, 45)
flagAssetButton.BorderSizePixel = 0
flagAssetButton.TextColor3 = Color3.fromRGB(235, 235, 235)
flagAssetButton.Font = Enum.Font.Gotham
flagAssetButton.TextSize = 11
flagAssetButton.Text = "Flag Asset"
flagAssetButton.Parent = actionRow

local actionState = Instance.new("TextLabel")
actionState.Size = UDim2.new(1, 0, 0, 14)
actionState.BackgroundTransparency = 1
actionState.Font = Enum.Font.Gotham
actionState.TextSize = 10
actionState.TextXAlignment = Enum.TextXAlignment.Left
actionState.TextYAlignment = Enum.TextYAlignment.Center
actionState.TextWrapped = false
actionState.TextTruncate = Enum.TextTruncate.AtEnd
actionState.TextColor3 = Color3.fromRGB(160, 160, 160)
actionState.Text = ""
actionState.Parent = root

local statusRow = Instance.new("Frame")
statusRow.Size = UDim2.new(1, 0, 0, 16)
statusRow.BackgroundTransparency = 1
statusRow.Parent = root

local assetStatusFrame = Instance.new("Frame")
assetStatusFrame.Size = UDim2.new(0, 100, 1, 0)
assetStatusFrame.BackgroundTransparency = 1
assetStatusFrame.Parent = statusRow

local assetDot = Instance.new("TextLabel")
assetDot.Size = UDim2.new(0, 10, 1, 0)
assetDot.BackgroundTransparency = 1
assetDot.Font = Enum.Font.GothamBold
assetDot.TextSize = 10
assetDot.TextXAlignment = Enum.TextXAlignment.Left
assetDot.TextColor3 = Color3.fromRGB(160, 160, 160)
assetDot.Text = "●"
assetDot.Parent = assetStatusFrame

local assetStatusText = Instance.new("TextLabel")
assetStatusText.Position = UDim2.new(0, 12, 0, 0)
assetStatusText.Size = UDim2.new(1, -12, 1, 0)
assetStatusText.BackgroundTransparency = 1
assetStatusText.Font = Enum.Font.Gotham
assetStatusText.TextSize = 10
assetStatusText.TextXAlignment = Enum.TextXAlignment.Left
assetStatusText.TextYAlignment = Enum.TextYAlignment.Center
assetStatusText.TextTruncate = Enum.TextTruncate.AtEnd
assetStatusText.TextColor3 = Color3.fromRGB(200, 200, 200)
assetStatusText.Text = "Asset: Idle"
assetStatusText.Parent = assetStatusFrame

local rojoStatusFrame = Instance.new("Frame")
rojoStatusFrame.Size = UDim2.new(0, 100, 1, 0)
rojoStatusFrame.BackgroundTransparency = 1
rojoStatusFrame.Parent = statusRow

local rojoDot = Instance.new("TextLabel")
rojoDot.Size = UDim2.new(0, 10, 1, 0)
rojoDot.BackgroundTransparency = 1
rojoDot.Font = Enum.Font.GothamBold
rojoDot.TextSize = 10
rojoDot.TextXAlignment = Enum.TextXAlignment.Left
rojoDot.TextColor3 = Color3.fromRGB(160, 160, 160)
rojoDot.Text = "●"
rojoDot.Parent = rojoStatusFrame

local rojoStatusText = Instance.new("TextLabel")
rojoStatusText.Position = UDim2.new(0, 12, 0, 0)
rojoStatusText.Size = UDim2.new(1, -12, 1, 0)
rojoStatusText.BackgroundTransparency = 1
rojoStatusText.Font = Enum.Font.Gotham
rojoStatusText.TextSize = 10
rojoStatusText.TextXAlignment = Enum.TextXAlignment.Left
rojoStatusText.TextYAlignment = Enum.TextYAlignment.Center
rojoStatusText.TextTruncate = Enum.TextTruncate.AtEnd
rojoStatusText.TextColor3 = Color3.fromRGB(160, 160, 160)
rojoStatusText.Text = "Rojo: Deactive"
rojoStatusText.Parent = rojoStatusFrame

local signalModuleName = "AssetTrustSignal"

local function updateActionButtonWidths()
	local totalWidth = actionRow.AbsoluteSize.X
	if totalWidth <= 0 then
		return
	end

	local gap = 8
	local eachWidth = math.max(70, math.floor((totalWidth - gap) / 2))
	copyRegexButton.Size = UDim2.new(0, eachWidth, 1, 0)
	flagAssetButton.Size = UDim2.new(0, eachWidth, 1, 0)
end

local function updateStatusLayout()
	local totalWidth = statusRow.AbsoluteSize.X
	if totalWidth <= 0 then
		return
	end

	local gap = 10
	local eachWidth = math.max(90, math.floor((totalWidth - gap) / 2))
	assetStatusFrame.Size = UDim2.new(0, eachWidth, 1, 0)
	rojoStatusFrame.Size = UDim2.new(0, eachWidth, 1, 0)
	rojoStatusFrame.Position = UDim2.new(0, eachWidth + gap, 0, 0)
end

local function parseSignalSource(sourceText)
	local parsed = {
		assetFileName = "",
		currentAsset = "",
		regexStatement = "",
		verifiedByApp = false,
		rojoActive = false,
		updatedAt = ""
	}

	parsed.assetFileName = sourceText:match('assetFileName%s*=%s*"(.-)"') or ""
	parsed.currentAsset = sourceText:match('currentAsset%s*=%s*"(.-)"') or ""
	parsed.regexStatement = sourceText:match('regexStatement%s*=%s*"(.-)"') or ""
	parsed.updatedAt = sourceText:match('updatedAt%s*=%s*"(.-)"') or ""
	local verifiedRaw = sourceText:match('verifiedByApp%s*=%s*(%a+)')
	parsed.verifiedByApp = (verifiedRaw == "true")
	local rojoRaw = sourceText:match('rojoActive%s*=%s*(%a+)')
	parsed.rojoActive = (rojoRaw == "true")

	return parsed
end

local function getWorkspaceMirrorFolder(assetFileName)
	if assetFileName == "" then
		return nil
	end

	local folderName = assetFileName:gsub("%.rbxm$", "")
	local workspaceRoot = workspace:FindFirstChild("WorkSpace")
	if not workspaceRoot then
		return nil
	end
	return workspaceRoot:FindFirstChild(folderName)
end

local function refreshFromSignal()
	local shared = game:GetService("ReplicatedStorage"):FindFirstChild("Shared")
	if not shared then
		assetStatusText.Text = "Asset: No Shared"
		assetDot.TextColor3 = Color3.fromRGB(255, 120, 120)
		rojoStatusText.Text = "Rojo: Deactive"
		rojoDot.TextColor3 = Color3.fromRGB(160, 160, 160)
		return
	end

	local signalModule = shared:FindFirstChild(signalModuleName)
	if not signalModule or not signalModule:IsA("ModuleScript") then
		assetStatusText.Text = "Asset: No Signal"
		assetDot.TextColor3 = Color3.fromRGB(255, 170, 120)
		rojoStatusText.Text = "Rojo: Deactive"
		rojoDot.TextColor3 = Color3.fromRGB(160, 160, 160)
		return
	end

	local signal = parseSignalSource(signalModule.Source)
	currentAsset.Text = signal.currentAsset ~= "" and signal.currentAsset or "Waiting for asset..."
	copyRegexButton:SetAttribute("RegexStatement", signal.regexStatement or "")
	flagAssetButton:SetAttribute("AssetFileName", signal.assetFileName or "")

	local workspaceMirror = getWorkspaceMirrorFolder(signal.assetFileName)

	if workspaceMirror and signal.verifiedByApp then
		assetStatusText.Text = "Asset: Verified"
		assetDot.TextColor3 = Color3.fromRGB(126, 231, 135)
	elseif workspaceMirror then
		assetStatusText.Text = "Asset: Pending"
		assetDot.TextColor3 = Color3.fromRGB(255, 215, 140)
	else
		assetStatusText.Text = "Asset: Waiting"
		assetDot.TextColor3 = Color3.fromRGB(255, 120, 120)
	end

	if signal.rojoActive then
		rojoStatusText.Text = "Rojo: Active"
		rojoDot.TextColor3 = Color3.fromRGB(126, 231, 135)
	else
		rojoStatusText.Text = "Rojo: Deactive"
		rojoDot.TextColor3 = Color3.fromRGB(160, 160, 160)
	end
end

copyRegexButton.MouseButton1Click:Connect(function()
	local regex = copyRegexButton:GetAttribute("RegexStatement")
	if typeof(regex) ~= "string" or regex == "" then
		actionState.Text = "No regex"
		actionState.TextColor3 = Color3.fromRGB(255, 180, 120)
		return
	end

	local copied = false

	-- StudioService clipboard API is the most reliable path across platforms.
	local studioService = game:GetService("StudioService")
	if studioService then
		copied = pcall(function()
			studioService:CopyToClipboard(regex)
		end)
	end

	-- Fallback for environments where StudioService clipboard is unavailable.
	if not copied and typeof(setclipboard) == "function" then
		copied = pcall(function()
			setclipboard(regex)
		end)
	end

	if copied then
		actionState.Text = "Regex copied"
		actionState.TextColor3 = Color3.fromRGB(126, 231, 135)
	else
		actionState.Text = "Copy blocked"
		actionState.TextColor3 = Color3.fromRGB(255, 180, 120)
	end
end)

flagAssetButton.MouseButton1Click:Connect(function()
	local assetFileName = flagAssetButton:GetAttribute("AssetFileName")
	if typeof(assetFileName) ~= "string" or assetFileName == "" then
		actionState.Text = "No current asset"
		actionState.TextColor3 = Color3.fromRGB(255, 180, 120)
		return
	end

	local workspaceRoot = workspace:FindFirstChild("WorkSpace")
	if not workspaceRoot then
		actionState.Text = "WorkSpace missing"
		actionState.TextColor3 = Color3.fromRGB(255, 180, 120)
		return
	end

	local sourceFolderName = assetFileName:gsub("%.rbxm$", "")
	local sourceFolder = workspaceRoot:FindFirstChild(sourceFolderName)
	if not sourceFolder then
		actionState.Text = "Mirror not found"
		actionState.TextColor3 = Color3.fromRGB(255, 180, 120)
		return
	end

	local flaggedRoot = workspace:FindFirstChild("AssetTrustFlagged")
	if not flaggedRoot then
		flaggedRoot = Instance.new("Folder")
		flaggedRoot.Name = "AssetTrustFlagged"
		flaggedRoot.Parent = workspace
	end

	local cloneName = sourceFolder.Name
	local counter = 2
	while flaggedRoot:FindFirstChild(cloneName) do
		cloneName = sourceFolder.Name .. "_" .. tostring(counter)
		counter += 1
	end

	local duplicate = sourceFolder:Clone()
	duplicate.Name = cloneName
	duplicate.Parent = flaggedRoot

	actionState.Text = "Flagged: " .. cloneName
	actionState.TextColor3 = Color3.fromRGB(126, 231, 135)
end)

openButton.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)

actionRow:GetPropertyChangedSignal("AbsoluteSize"):Connect(updateActionButtonWidths)
root:GetPropertyChangedSignal("AbsoluteSize"):Connect(updateActionButtonWidths)
statusRow:GetPropertyChangedSignal("AbsoluteSize"):Connect(updateStatusLayout)
root:GetPropertyChangedSignal("AbsoluteSize"):Connect(updateStatusLayout)

widget:GetPropertyChangedSignal("Enabled"):Connect(function()
	if widget.Enabled then
		updateActionButtonWidths()
		updateStatusLayout()
		refreshFromSignal()
	end
end)

task.spawn(function()
	while true do
		if widget.Enabled then
			refreshFromSignal()
		end
		task.wait(0.5)
	end
end)

refreshFromSignal()
updateActionButtonWidths()
updateStatusLayout()

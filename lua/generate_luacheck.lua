#!/usr/bin/env lua
if arg[1] == nil then
    print("Usage:")
    print("lua generate_config.lua (path_to_kms_client_repo)")
    print("")
    os.exit(1)
end

package.path=package.path..string.format(";%s/?.lua", arg[1])
require('lfs')

local Main = {}

Main.repo = arg[1]

Main.lib_paths = {
    'Resources/lua_foundation',
    'asset/lua/foundation',
}

Main.ignore_list = {
    [212]="unused argument",
    [213]="unused loop variable",
    [542]="empty if branch",
}

Main.find_modules = function()
    local list = {}
    for x, path in pairs(Main.lib_paths) do
        for file in lfs.dir(string.format('%s/%s', Main.repo, path)) do
            if string.find(file, '([-_%w]+.lua)') then
                table.insert(list, string.format('%s/%s', path, string.sub(file, 1, -5)))
            end
        end
    end
    return list
end

Main.find_globals = function()
    local orig = {}
    local dest = {}
    for k, v in pairs(_G) do
        orig[k] = v
    end
    for k, v in pairs(Main:find_modules()) do
        require(v)
    end
    for k, v in pairs(_G) do
        if orig[k] == nil then
            table.insert(dest, k)
        end
    end
    table.sort(dest)
    return dest
end

Main.execute = function()
    local global_list = Main:find_globals()

    print "codes = true\n"
    print "ignore = {"
    for k, v in pairs(Main.ignore_list) do
        print(string.format('  "%d", -- %s',k, v))
    end
    print "}\n"
    print "globals = {"
    for k, v in pairs(global_list) do
        print(string.format('    "%s",', v)) end
    print '    "KMS"'
    print "}"
end

Main.execute()


#!/usr/bin/env ruby
require "csv"
require "json"

unless 1 <= ARGV.size
  puts "引数指定してください"
  exit
end

ifile = ARGV[0]
ofile = "#{File.dirname(ifile)}/#{File.basename(ifile, '.tsv')}.json"

File.open(ofile, "w") do |f|
  lineno = 1

  f << "{\"data\":[\n"

  CSV.read(ifile, col_sep:"\t").each do |arr|
    unless lineno == 1
      f << arr.to_json
      f << ",\n"
    end
    lineno = lineno + 1
  end

  f << "]}"
end

puts "generated #{ofile}"

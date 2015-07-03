#!/usr/bin/env ruby

chars = []
('!'..'~').each {|c| chars.push(c) }
('ぁ'..'ん').each {|c| chars.push(c) }
('ァ'..'ヴ').each {|c| chars.push(c) }
('一'..'龠').each {|c| chars.push(c) }
chars.each {|c| print "#{c}\n"}
